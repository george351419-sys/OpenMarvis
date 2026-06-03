from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, SQLModel, create_engine

from openmarvis.scheduler.manager import ScheduleManager, ScheduleSpecError
from openmarvis.store.models import Schedule


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


@pytest.mark.asyncio
async def test_rehydrate_reloads_jobs_from_db_skipping_past_once(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/data.db")
    SQLModel.metadata.create_all(engine)
    # Seed: 1 future once, 1 past once (should skip), 1 interval, 1 cron
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    with Session(engine) as s:
        for sid, ttype, spec in [
            ("sch_future", "once", future),
            ("sch_past", "once", past),
            ("sch_int", "interval", "120"),
            ("sch_cron", "cron", "0 9 * * 1"),
        ]:
            s.add(Schedule(id=sid, origin_conv_id="c", trigger_type=ttype,
                             trigger_spec=spec, instruction="x", description="",
                             created_at=0))
        s.commit()

    mgr = ScheduleManager(db_dir=tmp_path, engine=engine, on_fire=MagicMock())
    await mgr.start()
    try:
        loaded = mgr.rehydrate()
        ids = {r.id for r in mgr.list()}
        assert {"sch_future", "sch_int", "sch_cron"}.issubset(ids)
        assert "sch_past" not in ids        # past once skipped
        assert loaded == 3                     # report skipped count externally
    finally:
        await mgr.shutdown()


@pytest.mark.asyncio
async def test_rehydrate_is_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/data.db")
    SQLModel.metadata.create_all(engine)
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    with Session(engine) as s:
        s.add(Schedule(id="sch_once", origin_conv_id="c", trigger_type="once",
                         trigger_spec=future, instruction="x", description="",
                         created_at=0))
        s.commit()

    mgr = ScheduleManager(db_dir=tmp_path, engine=engine, on_fire=MagicMock())
    await mgr.start()
    try:
        mgr.rehydrate()
        mgr.rehydrate()                       # second call must not crash
        ids = [r.id for r in mgr.list()]
        assert ids.count("sch_once") == 1
    finally:
        await mgr.shutdown()
