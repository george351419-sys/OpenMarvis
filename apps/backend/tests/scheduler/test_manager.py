from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from openmarvis.scheduler.manager import ScheduleManager, ScheduleSpecError


@pytest.mark.asyncio
async def test_add_once_creates_schedule_row(tmp_path):
    db_dir = tmp_path
    on_fire = MagicMock()
    mgr = ScheduleManager(db_dir=db_dir, engine=None, on_fire=on_fire)
    await mgr.start()
    try:
        run_at = datetime.now(UTC) + timedelta(days=365)
        sid = mgr.add_once(run_at, instruction="hi", description="x",
                            origin_conv_id="conv_a")
        assert sid.startswith("sch_")
        rows = mgr.list()
        assert any(r.id == sid for r in rows)
    finally:
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_add_interval_minimum_60s(tmp_path):
    mgr = ScheduleManager(db_dir=tmp_path, engine=None, on_fire=MagicMock())
    await mgr.start()
    try:
        with pytest.raises(ScheduleSpecError):
            mgr.add_interval(every_seconds=30, instruction="x",
                              description="", origin_conv_id="c")
    finally:
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_add_cron_rejects_invalid_expr(tmp_path):
    mgr = ScheduleManager(db_dir=tmp_path, engine=None, on_fire=MagicMock())
    await mgr.start()
    try:
        with pytest.raises(ScheduleSpecError):
            mgr.add_cron(expr="not a cron", instruction="x",
                          description="", origin_conv_id="c")
    finally:
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_cancel_removes_schedule(tmp_path):
    mgr = ScheduleManager(db_dir=tmp_path, engine=None, on_fire=MagicMock())
    await mgr.start()
    try:
        run_at = datetime.now(UTC) + timedelta(days=1)
        sid = mgr.add_once(run_at, instruction="x", description="",
                            origin_conv_id="c")
        ok = mgr.cancel(sid)
        assert ok is True
        assert all(r.id != sid for r in mgr.list())
    finally:
        await mgr.shutdown()
