from __future__ import annotations

from unittest.mock import MagicMock

from openmarvis.agents.sub.factory import SubAgentFactory
from openmarvis.tools.ask import PendingAskRegistry


def test_factory_builds_app_agent_with_12_tools_plus_ask():
    factory = SubAgentFactory(
        llm=MagicMock(), engine=MagicMock(),
        brave_key=None, browser_pool=None,
        ask_registry=PendingAskRegistry(),
    )
    agent = factory.build(
        agent_name="app-agent", conv_id="c1",
        workspace=MagicMock(output_dir="/tmp"),
        memory_store=MagicMock(),
        security=MagicMock(),
        event_sink=MagicMock(),
        user_settings=MagicMock(),
    )
    names = sorted(t.name for t in agent.tools.all())
    expected = sorted([
        "list_running_apps", "list_windows", "get_ax_tree",
        "read_window_text", "screenshot_window",
        "activate_app", "click_ax_node", "type_text",
        "select_menu", "quit_app",
        "vision_click", "vision_type",
        "ask_user",
    ])
    assert names == expected


def test_factory_app_agent_does_not_inject_exec_or_write():
    factory = SubAgentFactory(
        llm=MagicMock(), engine=MagicMock(),
        brave_key=None, browser_pool=None,
        ask_registry=PendingAskRegistry(),
    )
    agent = factory.build(
        agent_name="app-agent", conv_id="c1",
        workspace=MagicMock(output_dir="/tmp"),
        memory_store=MagicMock(),
        security=MagicMock(),
        event_sink=MagicMock(),
        user_settings=MagicMock(),
    )
    names = {t.name for t in agent.tools.all()}
    for forbidden in ("shell", "python", "write_file", "delete", "edit_file"):
        assert forbidden not in names
