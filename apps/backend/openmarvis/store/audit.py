from __future__ import annotations

import time

from sqlmodel import Session

from .models import WriteAudit


def record_write(engine, *, conv_id: str, path: str) -> None:
    with Session(engine) as s:
        s.add(WriteAudit(conv_id=conv_id, path=str(path), ts=int(time.time())))
        s.commit()


def writes_for_conv(engine, conv_id: str, *, since_ts: int = 0) -> list[WriteAudit]:
    from sqlmodel import select

    with Session(engine) as s:
        rows = s.exec(
            select(WriteAudit).where(WriteAudit.conv_id == conv_id, WriteAudit.ts >= since_ts)
        ).all()
        return list(rows)
