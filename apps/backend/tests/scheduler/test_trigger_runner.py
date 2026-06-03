from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from openmarvis.scheduler.trigger_runner import run_scheduled_trigger


@pytest.mark.asyncio
async def test_runner_creates_virtual_conv_and_persists_notification(tmp_path):
    engine = MagicMock()

    # Stub Schedule row read
    from openmarvis.store.models import Schedule
    sch = Schedule(id="sch_1", origin_conv_id="conv_a", trigger_type="once",
                    trigger_spec="2099-01-01T00:00:00+00:00",
                    instruction="hi", description="d",
                    created_at=0, next_run_at=None,
                    last_run_at=None, last_status=None)
    read_fn = MagicMock(return_value=sch)

    runner = AsyncMock(return_value="run finished")
    state = MagicMock()
    state.engine = engine
    state.workspaces = MagicMock()
    state.workspaces.get_or_create = lambda cid: MagicMock(output_dir=str(tmp_path))

    notify_persist = MagicMock()
    await run_scheduled_trigger(
        schedule_id="sch_1",
        state=state,
        load_schedule=read_fn,
        run_chat=runner,
        persist_notification=notify_persist,
    )
    runner.assert_awaited_once()
    notify_persist.assert_called_once()
    call_args = notify_persist.call_args.kwargs
    assert call_args["origin_conv_id"] == "conv_a"
    assert call_args["status"] in ("success", "failed")
