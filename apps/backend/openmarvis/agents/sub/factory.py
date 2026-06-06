from __future__ import annotations

import ulid

from ...app_automation.ax_backend import AXBackend
from ...app_automation.cliclick_runner import CliclickRunner
from ...app_automation.tools_app import (
    ActivateAppTool,
    ClickAXNodeTool,
    GetAXTreeTool,
    ListRunningAppsTool,
    ListWindowsTool,
    QuitAppTool,
    ReadWindowTextTool,
    ScreenshotWindowTool,
    SelectMenuTool,
    TypeTextTool,
    VisionClickTool,
    VisionTypeTool,
)
from ...app_automation.vision_backend import VisionBackend
from ...browser.pool import BrowserPool
from ...browser.tools_action import ClickTool, FillTool, SubmitFormTool
from ...browser.tools_capture import ScreenshotTool
from ...browser.tools_eval import EvaluateTool
from ...browser.tools_extract import ExtractTextTool, ListElementsTool
from ...browser.tools_nav import CurrentUrlTool, GoBackTool, NavigateTool
from ...browser.tools_wait import WaitForSelectorTool
from ...computer.tools_apps import AppStatusTool, CloseAppTool, KillProcessTool, OpenAppTool
from ...computer.tools_clipboard import ClipboardReadTool, ClipboardWriteTool
from ...computer.tools_info import DiskUsageTool, FindProcessTool, ListProcessesTool, SystemInfoTool
from ...computer.tools_session import LockScreenTool, NotificationTool, SleepSystemTool
from ...computer.tools_settings import (
    BrightnessGetTool,
    BrightnessSetTool,
    OpenSettingsPaneTool,
    VolumeGetTool,
    VolumeMuteTool,
    VolumeSetTool,
)
from ...llm.event_sink import QueueEventSink
from ...memory.store import MemoryStore
from ...prompts import load_prompt
from ...security.policy import SecurityGate
from ...tools.ask import AskUserTool, PendingAskRegistry
from ...tools.base import Tool
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
from ...tools.convert_file import ConvertFileTool
from ...tools.read_file import ReadFileTool
from ...tools.registry import ToolRegistry
from ...tools.search_chunk import SearchChunkTool
from ...tools.search_file import SearchFileTool
from ...tools.spotlight import SpotlightTool
from ...tools.ai_search import AiSearchTool
from ...tools.fs_search import FsSearchContentTool, FsSearchFileTool
from ...tools.invoice import InvoiceDetectionTool, InvoiceParsingTool
from ...tools.web import WebFetchTool, WebSearchTool
from ...workspace.manager import Workspace
from ..base import AgentBase


def _build_registry(agent_name: str, *, llm, engine, brave_key: str | None,  # noqa: C901
                     browser_pool: BrowserPool | None = None,
                     ask_registry: PendingAskRegistry | None = None,
                     coze_key: str | None = None) -> ToolRegistry:
    reg = ToolRegistry()
    tools: tuple[Tool, ...]
    if agent_name == "file-agent":
        tools = (ReadTextTool(), ReadFileTool(),
                  WriteFileTool(engine=engine),
                  EditFileTool(engine=engine), DeleteTool(),
                  ListDirTool(), SearchFilesTool(),
                  SearchFileTool(engine=engine),
                  SearchChunkTool(engine=engine),
                  ConvertFileTool(engine=engine),
                  ShellExecutorTool(), PythonExecutorTool(),
                  AnalyzeImageTool(llm=llm),
                  SpotlightTool(),
                  FsSearchFileTool(),
                  FsSearchContentTool(),
                  InvoiceDetectionTool(llm=llm),
                  InvoiceParsingTool(llm=llm),
                  AiSearchTool(api_key=brave_key, llm=llm))
    elif agent_name == "search-agent":
        tools = (WebSearchTool(api_key=brave_key), WebFetchTool(),
                  PythonExecutorTool())
    elif agent_name == "browser-agent":
        assert browser_pool is not None, "browser-agent 需要 BrowserPool"
        assert ask_registry is not None, "browser-agent 需要 PendingAskRegistry"
        tools = (NavigateTool(pool=browser_pool),
                  CurrentUrlTool(pool=browser_pool),
                  GoBackTool(pool=browser_pool),
                  ClickTool(pool=browser_pool),
                  FillTool(pool=browser_pool),
                  SubmitFormTool(pool=browser_pool),
                  WaitForSelectorTool(pool=browser_pool),
                  ScreenshotTool(pool=browser_pool),
                  ExtractTextTool(pool=browser_pool),
                  ListElementsTool(pool=browser_pool),
                  EvaluateTool(pool=browser_pool),
                  AskUserTool(registry=ask_registry))
    elif agent_name == "computer-agent":
        assert ask_registry is not None, "computer-agent 需要 PendingAskRegistry"
        tools = (SystemInfoTool(), DiskUsageTool(),
                  ListProcessesTool(), FindProcessTool(),
                  OpenAppTool(), CloseAppTool(), AppStatusTool(), KillProcessTool(),
                  VolumeGetTool(), VolumeSetTool(), VolumeMuteTool(),
                  BrightnessGetTool(), BrightnessSetTool(),
                  OpenSettingsPaneTool(),
                  ClipboardReadTool(), ClipboardWriteTool(),
                  LockScreenTool(), SleepSystemTool(), NotificationTool(),
                  AskUserTool(registry=ask_registry))
    elif agent_name == "app-agent":
        assert ask_registry is not None, "app-agent 需要 PendingAskRegistry"
        ax = AXBackend()
        vision = VisionBackend(llm=llm)
        cliclick = CliclickRunner()
        tools = (ListRunningAppsTool(ax=ax),
                  ListWindowsTool(ax=ax),
                  GetAXTreeTool(ax=ax),
                  ReadWindowTextTool(ax=ax),
                  ScreenshotWindowTool(ax=ax),
                  ActivateAppTool(ax=ax),
                  ClickAXNodeTool(ax=ax),
                  TypeTextTool(ax=ax),
                  SelectMenuTool(ax=ax),
                  QuitAppTool(ax=ax),
                  VisionClickTool(ax=ax, vision=vision, cliclick=cliclick),
                  VisionTypeTool(ax=ax, vision=vision, cliclick=cliclick),
                  AskUserTool(registry=ask_registry))
    else:
        raise ValueError(f"unsupported sub agent: {agent_name}")
    for t in tools:
        reg.register(t)
    return reg


class SubAgentFactory:
    def __init__(self, *, llm, engine, brave_key: str | None = None,
                 browser_pool: BrowserPool | None = None,
                 ask_registry: PendingAskRegistry | None = None):
        self.llm = llm
        self.engine = engine
        self.brave_key = brave_key
        self.browser_pool = browser_pool
        self.ask_registry = ask_registry

    def build(self, *, agent_name: str, conv_id: str,
              workspace: Workspace, memory_store: MemoryStore,
              security: SecurityGate, event_sink: QueueEventSink,
              user_settings) -> AgentBase:
        registry = _build_registry(agent_name, llm=self.llm, engine=self.engine,
                                    brave_key=self.brave_key,
                                    browser_pool=self.browser_pool,
                                    ask_registry=self.ask_registry)
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
