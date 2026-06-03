from __future__ import annotations

import time

from sqlmodel import Session, select

from .models import ScheduleNotification


def persist_notification(*, engine, origin_conv_id: str, schedule_id: str,
                          virtual_conv_id: str, summary: str, status: str) -> None:
    with Session(engine) as ses:
        ses.add(ScheduleNotification(
            origin_conv_id=origin_conv_id,
            schedule_id=schedule_id,
            virtual_conv_id=virtual_conv_id,
            summary=summary, status=status, read=False,
            created_at=int(time.time()),
        ))
        ses.commit()


def list_unread(engine, *, origin_conv_id: str) -> list[ScheduleNotification]:
    with Session(engine) as ses:
        rows = ses.exec(
            select(ScheduleNotification)
                .where(ScheduleNotification.origin_conv_id == origin_conv_id)
                .where(ScheduleNotification.read == False)              # noqa: E712
        ).all()
        return list(rows)


def mark_read(engine, *, notification_id: int) -> None:
    with Session(engine) as ses:
        row = ses.get(ScheduleNotification, notification_id)
        if row is not None:
            row.read = True
            ses.add(row)
            ses.commit()
