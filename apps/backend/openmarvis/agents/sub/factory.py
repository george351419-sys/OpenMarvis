from __future__ import annotations

import ulid

from ...llm.event_sink import QueueEventSink
from ...memory.store import MemoryStore
from ...prompts import load_prompt
from ...security.policy import SecurityGate
from ...tools.exec import PythonExecutorTool, ShellExecutorTool
from ...tools.fs import (
    DeleteTool,
    EditFileTool,
    ListDirTool,
    ReadTextTool,
    SearchFilesTool,
    WriteFileTool,
)
from ...tools.image import AnalyzeImageTool
from ...tools.registry import ToolRegistry
from ...tools.web import WebFetchTool, WebSearchTool
from ...workspace.manager import Workspace
from ..base import AgentBase


def _build_registry(agent_name: str, *, llm, engine, brave_key: str | None) -> ToolRegistry:
    reg = ToolRegistry()
    if agent_name == "file-agent":
        for t in (ReadTextTool(), WriteFileTool(engine=engine),
                  EditFileTool(engine=engine), DeleteTool(),
                  ListDirTool(), SearchFilesTool(),
                  ShellExecutorTool(), PythonExecutorTool(),
                  AnalyzeImageTool(llm=llm)):
            reg.register(t)
    elif agent_name == "search-agent":
        for t in (WebSearchTool(api_key=brave_key), WebFetchTool(),
                  PythonExecutorTool()):
            reg.register(t)
    else:
        raise ValueError(f"unsupported sub agent: {agent_name}")
    return reg


class SubAgentFactory:
    def __init__(self, *, llm, engine, brave_key: str | None = None):
        self.llm = llm
        self.engine = engine
        self.brave_key = brave_key

    def build(self, *, agent_name: str, conv_id: str,
              workspace: Workspace, memory_store: MemoryStore,
              security: SecurityGate, event_sink: QueueEventSink,
              user_settings) -> AgentBase:
        registry = _build_registry(agent_name, llm=self.llm, engine=self.engine,
                                    brave_key=self.brave_key)
        return AgentBase(
            name=agent_name,
            agent_id=f"sa-{ulid.new().str.lower()}",
            conv_id=conv_id,
            system_prompt=load_prompt(agent_name.replace("-", "_")),
            llm=self.llm,
            tool_registry=registry,
            workspace=workspace,
            memory_store=memory_store,
            security=security,
            event_sink=event_sink,
            user_settings=user_settings,
            max_iterations=20,
        )
