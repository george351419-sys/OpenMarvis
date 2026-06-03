from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session, select

from openmarvis.store.db import create_engine, init_db
from openmarvis.store.models import Schedule


def test_schedule_table_roundtrip(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    s = Schedule(
        id="sch_001", origin_conv_id="conv_abc",
        trigger_type="once",
        trigger_spec="2026-12-31T10:00:00+00:00",
        instruction="run weekly report",
        description="2026 年终报告",
        created_at=int(datetime.now(UTC).timestamp()),
        next_run_at=None, last_run_at=None, last_status=None,
    )
    with Session(engine) as ses:
        ses.add(s)
        ses.commit()
    with Session(engine) as ses:
        rows = ses.exec(select(Schedule)).all()
        assert len(rows) == 1
        assert rows[0].trigger_type == "once"


def test_schedule_notification_table_roundtrip(tmp_path):
    from openmarvis.store.models import ScheduleNotification
    engine = create_engine(tmp_path / "db2.sqlite")
    init_db(engine)
    n = ScheduleNotification(
        id=None, origin_conv_id="conv_x", schedule_id="sch_001",
        virtual_conv_id="sched_001_1700000000",
        summary="run done", status="success", read=False,
        created_at=1700000000,
    )
    with Session(engine) as ses:
        ses.add(n)
        ses.commit()
    with Session(engine) as ses:
        rows = ses.exec(select(ScheduleNotification)).all()
        assert len(rows) == 1
        assert rows[0].read is False
