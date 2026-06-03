from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger(__name__)


async def run_scheduled_trigger(
    *,
    schedule_id: str,
    state: Any,
    load_schedule: Callable[[Any, str], Any],
    run_chat: Callable[[str, str, Any], Awaitable[str]],
    persist_notification: Callable[..., None],
) -> None:
    """虚拟会话执行入口：被 ScheduleManager 的 on_fire 调用。

    依赖通过参数注入，便于测试。
    """
    sch = load_schedule(state.engine, schedule_id)
    if sch is None:
        log.warning("schedule %s vanished before fire", schedule_id)
        return
    virtual_conv_id = f"sched_{schedule_id}_{int(time.time())}"
    try:
        summary = await run_chat(virtual_conv_id, sch.instruction, state)
        status = "success"
    except Exception as e:                            # pragma: no cover (paths covered via tests)
        log.exception("scheduled trigger failed")
        summary = f"failed: {e}"
        status = "failed"
    persist_notification(
        engine=state.engine,
        origin_conv_id=sch.origin_conv_id,
        schedule_id=schedule_id,
        virtual_conv_id=virtual_conv_id,
        summary=summary[:500],
        status=status,
    )
