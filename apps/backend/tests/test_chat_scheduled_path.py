from __future__ import annotations

from openmarvis.scheduler.trigger_filter import filter_registry_for_scheduled_run
from openmarvis.tools.registry import ToolRegistry


def test_filter_drops_scheduler_tools_and_ask_user():
    reg = ToolRegistry()
    from openmarvis.scheduler.tools_schedule import (
        CancelScheduleTool,
        CreateScheduleTool,
        ListSchedulesTool,
    )
    from openmarvis.tools.ask import AskUserTool, PendingAskRegistry
    from openmarvis.tools.web import WebSearchTool

    reg.register(CreateScheduleTool())
    reg.register(ListSchedulesTool())
    reg.register(CancelScheduleTool())
    reg.register(AskUserTool(registry=PendingAskRegistry()))
    reg.register(WebSearchTool())

    filtered = filter_registry_for_scheduled_run(reg)
    names = {t.name for t in filtered.all()}
    assert "create_schedule" not in names
    assert "list_schedules" not in names
    assert "cancel_schedule" not in names
    assert "ask_user" not in names
    assert "web_search" in names
