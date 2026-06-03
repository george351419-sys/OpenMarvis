from __future__ import annotations

from unittest.mock import MagicMock

from openmarvis.scheduler.trigger_filter import filter_registry_for_scheduled_run
from openmarvis.tools.registry import ToolRegistry


def test_filter_drops_scheduler_and_ask_tools():
    reg = ToolRegistry()
    t_keep = MagicMock(spec=["name", "available_to"])
    t_keep.name = "read_file"
    t_keep.available_to = ("main",)
    t_drop_create = MagicMock(spec=["name", "available_to"])
    t_drop_create.name = "create_schedule"
    t_drop_create.available_to = ("main",)
    t_drop_ask = MagicMock(spec=["name", "available_to"])
    t_drop_ask.name = "ask_user"
    t_drop_ask.available_to = ("main",)

    reg._tools = {t.name: t for t in (t_keep, t_drop_create, t_drop_ask)}
    out = filter_registry_for_scheduled_run(reg)
    names = {t.name for t in out.all()}
    assert "read_file" in names
    assert "create_schedule" not in names
    assert "ask_user" not in names
