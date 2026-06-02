from __future__ import annotations

import ulid

from ..llm.event_sink import QueueEventSink
from ..memory.store import MemoryStore
from ..prompts import load_prompt
from ..security.policy import SecurityGate
from ..store.sub_agents import SubAgentStore
from ..tools.ask import AskUserTool, PendingAskRegistry
from ..tools.dispatch import DispatchTaskTool
from ..tools.exec import PythonExecutorTool, ShellExecutorTool
from ..tools.fs import (
    DeleteTool,
    EditFileTool,
    ListDirTool,
    ReadTextTool,
    SearchFilesTool,
    WriteFileTool,
)
from ..tools.image import AnalyzeImageTool
from ..tools.present import PresentResultTool
from ..tools.registry import ToolRegistry
from ..tools.web import WebFetchTool, WebSearchTool
from ..workspace.manager import Workspace
from .base import AgentBase
from .sub.factory import SubAgentFactory


def _render_workspace_block(ws: Workspace) -> str:
    return (
        f"- 根目录:      {ws.root}/\n"
        f"- 中间产物:    {ws.temp_dir}/\n"
        f"- 最终产物:    {ws.output_dir}/\n"
        f"- 上传文件:    {ws.uploads_dir}/"
    )


def build_main_agent(
    *,
    conv_id: str,
    llm,
    engine,
    brave_key: str | None,
    workspace: Workspace,
    memory_store: MemoryStore,
    security: SecurityGate,
    event_sink: QueueEventSink,
    user_settings,
    ask_registry: PendingAskRegistry | None = None,
    browser_pool=None,
) -> AgentBase:
    if ask_registry is None:
        ask_registry = PendingAskRegistry()
    sub_store = SubAgentStore(engine)
    factory = SubAgentFactory(llm=llm, engine=engine, brave_key=brave_key,
                              browser_pool=browser_pool,
                              ask_registry=ask_registry)
    reg = ToolRegistry()
    for t in (
        ReadTextTool(),
        WriteFileTool(engine=engine),
        EditFileTool(engine=engine),
        DeleteTool(),
        ListDirTool(),
        SearchFilesTool(),
        ShellExecutorTool(),
        PythonExecutorTool(),
        WebSearchTool(api_key=brave_key),
        WebFetchTool(),
        AnalyzeImageTool(llm=llm),
        AskUserTool(registry=ask_registry),
        DispatchTaskTool(factory=factory, sub_store=sub_store),
        PresentResultTool(sub_store=sub_store),
    ):
        reg.register(t)

    raw_prompt = load_prompt("main_agent")
    rendered = raw_prompt.replace("{{ WORKSPACE_BLOCK }}", _render_workspace_block(workspace))
    return AgentBase(
        name="main",
        agent_id=f"main-{ulid.new().str.lower()}",
        conv_id=conv_id,
        system_prompt=rendered,
        llm=llm,
        tool_registry=reg,
        workspace=workspace,
        memory_store=memory_store,
        security=security,
        event_sink=event_sink,
        user_settings=user_settings,
        max_iterations=30,
    )
