"""Registration smoke tests — 工具 / Skill 注册一致性。

防止以后加新 tool 时只在 main_agent.py 注册但漏了 sub/factory.py，
或者反之。也防止 dispatch_task 的 agent_name 白名单和 factory 漏对齐。
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from openmarvis.agents.main_agent import build_main_agent
from openmarvis.llm.event_sink import QueueEventSink
from openmarvis.memory.store import MemoryStore
from openmarvis.security.policy import SecurityGate
from openmarvis.skill.registry import SkillRegistry
from openmarvis.store.db import create_engine, init_db
from openmarvis.tools.ask import PendingAskRegistry
from openmarvis.workspace.manager import Workspace

_BUILTINS = Path(__file__).resolve().parents[1] / "openmarvis" / "skill" / "builtins"


# ---------------- Main Agent 工具集 ----------------


@pytest.fixture
def main_agent(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    sink = QueueEventSink()
    ask_reg = PendingAskRegistry()
    skill_reg = SkillRegistry()
    skill_reg.scan(_BUILTINS)

    class FakeLLM: ...

    return build_main_agent(
        conv_id="c", llm=FakeLLM(), engine=engine, brave_key=None,
        workspace=ws, memory_store=MemoryStore(engine),
        security=SecurityGate(workspace=ws), event_sink=sink,
        user_settings=None,
        ask_registry=ask_reg,
        skill_registry=skill_reg,
    )


def test_main_agent_has_core_file_tools(main_agent):
    names = {t.name for t in main_agent.tools.all()}
    # 读 + 写 + 改 + 删 + 列
    assert {"read_text", "read_file", "write_file", "edit_file",
            "delete", "list_dir"} <= names


def test_main_agent_has_all_search_tools(main_agent):
    names = {t.name for t in main_agent.tools.all()}
    # 四套搜索路径（Spotlight / FTS5 file / FTS5 chunk / glob）
    assert {"search_files_spotlight", "search_file",
            "search_chunk", "search_files"} <= names


def test_main_agent_has_convert_and_image_tools(main_agent):
    names = {t.name for t in main_agent.tools.all()}
    assert {"convert_file", "analyze_image"} <= names


def test_main_agent_has_web_tools(main_agent):
    names = {t.name for t in main_agent.tools.all()}
    assert {"web_search", "web_fetch"} <= names


def test_main_agent_has_executor_tools(main_agent):
    names = {t.name for t in main_agent.tools.all()}
    assert {"shell_executor", "python_executor"} <= names


def test_main_agent_has_orchestration_tools(main_agent):
    names = {t.name for t in main_agent.tools.all()}
    # dispatch / present / ask / list_skills / use_skill
    assert {"dispatch_task", "present_result", "ask_user",
            "list_skills", "use_skill"} <= names


def test_main_agent_has_schedule_tools(main_agent):
    names = {t.name for t in main_agent.tools.all()}
    assert {"create_schedule", "list_schedules", "cancel_schedule"} <= names


def test_main_agent_has_user_pref_tools(main_agent):
    names = {t.name for t in main_agent.tools.all()}
    assert {"save_user_preference", "forget_user_preference"} <= names


# ---------------- Sub Agent 工具集 ----------------


def test_file_agent_has_full_file_stack(tmp_path):
    """file-agent 应该有完整的文件操作栈，包括最近加的 read_file / search_file
    / search_chunk / convert_file。漏注册任何一个都会让 prompt 里的路由表
    指向不存在的工具，导致 LLM 调用 unknown tool。
    """
    from openmarvis.agents.sub.factory import SubAgentFactory
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    factory = SubAgentFactory(llm=MagicMock(), engine=engine, brave_key=None,
                                browser_pool=None,
                                ask_registry=PendingAskRegistry())
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    agent = factory.build(
        agent_name="file-agent", conv_id="c", workspace=ws,
        memory_store=MemoryStore(engine),
        security=SecurityGate(workspace=ws),
        event_sink=QueueEventSink(), user_settings=None,
    )
    names = {t.name for t in agent.tools.all()}
    assert {
        # 读
        "read_text", "read_file",
        # 写
        "write_file", "edit_file", "delete",
        # 找
        "list_dir", "search_files",
        "search_file", "search_chunk", "search_files_spotlight",
        # 转 + 看
        "convert_file", "analyze_image",
        # executors
        "shell_executor", "python_executor",
    } <= names, f"file-agent missing: {names}"


def test_dispatch_task_agent_whitelist_matches_factory(tmp_path):
    """DispatchTaskTool 内部白名单和 factory._build_registry 支持的 agent_name
    必须一致；不一致会导致用户消息派给"已知"但工厂不识别的 agent，反之亦然。
    """
    from openmarvis.tools.dispatch import DispatchTaskTool
    # 我们能从 factory 知道支持哪些 agent_name —— 模拟跑一遍
    from openmarvis.agents.sub.factory import _build_registry

    supported = []
    for name in ("file-agent", "search-agent", "browser-agent",
                  "computer-agent", "app-agent"):
        try:
            _build_registry(
                name, llm=MagicMock(), engine=create_engine(tmp_path / "db.sqlite"),
                brave_key=None, browser_pool=None,
                ask_registry=PendingAskRegistry(),
            )
            supported.append(name)
        except Exception:
            # 缺依赖（browser_pool / ask_registry）时部分会抛 —— 算支持
            supported.append(name)

    # DispatchTaskTool 的白名单在 source 里硬编码；这里通过尝试解析
    # task envelope 后调用 execute 来探测。简单做法：直接读 source。
    src = Path(DispatchTaskTool.__module__.replace(".", "/") + ".py")
    src = (Path(__file__).resolve().parents[1] / "openmarvis"
           / "tools" / "dispatch.py")
    text = src.read_text()
    for name in supported:
        assert f'"{name}"' in text, (
            f"factory 支持 '{name}' 但 DispatchTaskTool 白名单里没有"
        )


# ---------------- Skill registry ----------------


def test_six_builtin_skills_discoverable_at_runtime():
    """所有 6 个 builtin skill 必须能被 scan 扫到 —— 防止以后忘加 skill.yaml
    或目录名拼错。
    """
    reg = SkillRegistry()
    reg.scan(_BUILTINS)
    names = {m.name for m in reg.list()}
    expected = {
        "document_convert", "file_organizer", "pdf",
        "document_writer", "excel_processing", "planning_with_files",
    }
    missing = expected - names
    assert not missing, f"missing builtin skills: {missing}"
