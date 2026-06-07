from __future__ import annotations

import ulid

from ..llm.event_sink import QueueEventSink
from ..memory.store import MemoryStore
from ..prompts import load_prompt
from ..security.policy import SecurityGate
from ..store.sub_agents import SubAgentStore
from ..tools.ask import AskUserTool, PendingAskRegistry
from ..tools.base import Tool
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
from ..tools.send_file import SendFileTool
from ..tools.convert_file import ConvertFileTool
from ..tools.read_file import ReadFileTool
from ..tools.registry import ToolRegistry
from ..tools.search_chunk import SearchChunkTool
from ..tools.search_file import SearchFileTool
from ..tools.spotlight import SpotlightTool
from ..tools.user_pref import ForgetUserPreferenceTool, SaveUserPreferenceTool
from ..tools.ai_search import AiSearchTool
from ..tools.fs_search import FsSearchContentTool, FsSearchFileTool
from ..tools.invoice import InvoiceDetectionTool, InvoiceParsingTool
from ..tools.search_image import SearchImageTool
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
    coze_key: str | None = None,
    workspace: Workspace,
    memory_store: MemoryStore,
    security: SecurityGate,
    event_sink: QueueEventSink,
    user_settings,
    ask_registry: PendingAskRegistry | None = None,
    browser_pool=None,
    scheduler_manager=None,
    skill_registry=None,
) -> AgentBase:
    if ask_registry is None:
        ask_registry = PendingAskRegistry()
    if user_settings is not None:
        user_settings.scheduler_manager = scheduler_manager
    sub_store = SubAgentStore(engine)
    factory = SubAgentFactory(llm=llm, engine=engine, brave_key=brave_key,
                              browser_pool=browser_pool,
                              ask_registry=ask_registry)
    reg = ToolRegistry()
    main_tools: tuple[Tool, ...] = (
        ReadTextTool(),
        ReadFileTool(),
        WriteFileTool(engine=engine),
        EditFileTool(engine=engine),
        DeleteTool(ask_registry=ask_registry),
        ListDirTool(),
        SearchFilesTool(),
        ShellExecutorTool(),
        PythonExecutorTool(),
        WebSearchTool(api_key=brave_key),
        WebFetchTool(),
        AiSearchTool(api_key=brave_key, llm=llm),
        FsSearchFileTool(),
        FsSearchContentTool(),
        InvoiceDetectionTool(llm=llm),
        InvoiceParsingTool(llm=llm),
        SearchImageTool(engine=engine),
        AnalyzeImageTool(llm=llm),
        AskUserTool(registry=ask_registry),
        DispatchTaskTool(factory=factory, sub_store=sub_store),
        PresentResultTool(sub_store=sub_store),
        SpotlightTool(),
        SearchFileTool(engine=engine),
        SearchChunkTool(engine=engine),
        ConvertFileTool(engine=engine),
        SaveUserPreferenceTool(),
        ForgetUserPreferenceTool(),
        SendFileTool(),
    )
    for t in main_tools:
        reg.register(t)

    from ..scheduler.tools_schedule import (
        CancelScheduleTool,
        CreateScheduleTool,
        ListSchedulesTool,
        ModifyScheduleTool,
    )
    schedule_tools: tuple[Tool, ...] = (
        CreateScheduleTool(), ListSchedulesTool(), CancelScheduleTool(),
        ModifyScheduleTool(),
    )
    for t in schedule_tools:
        reg.register(t)

    if skill_registry is not None:
        from ..skill.tools_skill import ListSkillsTool, UseSkillTool
        reg.register(UseSkillTool(skill_registry=skill_registry,
                                    parent_tool_registry=reg, llm=llm))
        reg.register(ListSkillsTool(skill_registry=skill_registry))

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
