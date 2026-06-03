from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import Session, select

from ..store.models import ScheduleNotification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/unread")
async def list_unread(request: Request, origin_conv_id: str | None = None) -> list[dict]:
    engine = request.app.state.om.engine
    with Session(engine) as s:
        q = select(ScheduleNotification).where(
            ScheduleNotification.read == False)              # noqa: E712
        if origin_conv_id is not None:
            q = q.where(ScheduleNotification.origin_conv_id == origin_conv_id)
        q = q.order_by(ScheduleNotification.created_at.desc())
        rows = s.exec(q).all()
    return [
        {
            "id": r.id,
            "origin_conv_id": r.origin_conv_id,
            "schedule_id": r.schedule_id,
            "virtual_conv_id": r.virtual_conv_id,
            "summary": r.summary,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post("/{notification_id}/read")
async def mark_read(notification_id: int, request: Request) -> dict:
    engine = request.app.state.om.engine
    with Session(engine) as s:
        row = s.get(ScheduleNotification, notification_id)
        if row is None:
            raise HTTPException(404, "not found")
        row.read = True
        s.add(row)
        s.commit()
    return {"ok": True}
