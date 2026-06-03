from __future__ import annotations

from ..tools.registry import ToolRegistry

_DROPPED_PREFIXES = ("create_schedule", "list_schedules", "cancel_schedule")
_DROPPED_EXACT = {"ask_user"}


def filter_registry_for_scheduled_run(reg: ToolRegistry) -> ToolRegistry:
    """返回新 registry：去掉 scheduler.* 与 ask_user。"""
    out = ToolRegistry()
    for t in reg.all():
        if t.name in _DROPPED_EXACT:
            continue
        if any(t.name == p for p in _DROPPED_PREFIXES):
            continue
        out.register(t)
    return out
