from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from openmarvis.store.models import ScheduleNotification
from openmarvis.store.notifications import (
    list_unread,
    mark_read,
    persist_notification,
)


def _engine(tmp_path):
    e = create_engine(f"sqlite:///{tmp_path}/data.db")
    SQLModel.metadata.create_all(e)
    return e


def test_persist_then_list_then_mark_read(tmp_path):
    e = _engine(tmp_path)
    persist_notification(engine=e, origin_conv_id="conv_a",
                          schedule_id="sch_1", virtual_conv_id="vc_1",
                          summary="hi", status="success")
    persist_notification(engine=e, origin_conv_id="conv_a",
                          schedule_id="sch_1", virtual_conv_id="vc_2",
                          summary="bye", status="failed")
    persist_notification(engine=e, origin_conv_id="conv_b",
                          schedule_id="sch_2", virtual_conv_id="vc_3",
                          summary="other", status="success")

    rows_a = list_unread(e, origin_conv_id="conv_a")
    assert {r.summary for r in rows_a} == {"hi", "bye"}
    rows_b = list_unread(e, origin_conv_id="conv_b")
    assert len(rows_b) == 1 and rows_b[0].summary == "other"

    mark_read(e, notification_id=rows_a[0].id)
    remaining = list_unread(e, origin_conv_id="conv_a")
    assert len(remaining) == 1
    assert all(r.id != rows_a[0].id for r in remaining)

    # mark_read on missing id is a no-op (no exception)
    mark_read(e, notification_id=99999)
    with Session(e) as s:
        assert s.get(ScheduleNotification, rows_a[0].id).read is True
