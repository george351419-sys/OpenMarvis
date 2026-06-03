from __future__ import annotations

import time

import ulid
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from ..store.models import Conversation, Message

router = APIRouter(prefix="/conversations", tags=["conversations"])


class CreateConvRequest(BaseModel):
    title: str = ""


@router.post("")
async def create_conv(req: CreateConvRequest, request: Request) -> dict:
    engine = request.app.state.om.engine
    cid = f"conv_{ulid.new().str.lower()}"
    now = int(time.time())
    with Session(engine) as s:
        s.add(Conversation(id=cid, title=req.title, created_at=now, updated_at=now))
        s.commit()
    return {"id": cid, "title": req.title, "created_at": now, "updated_at": now}


@router.get("")
async def list_conv(request: Request) -> list[dict]:
    engine = request.app.state.om.engine
    with Session(engine) as s:
        rows = s.exec(select(Conversation).where(Conversation.archived == False)  # noqa: E712
                       .order_by(Conversation.updated_at.desc())).all()  # type: ignore[attr-defined]
    return [{"id": r.id, "title": r.title, "created_at": r.created_at,
             "updated_at": r.updated_at} for r in rows]


@router.delete("/{conv_id}")
async def delete_conv(conv_id: str, request: Request) -> dict:
    engine = request.app.state.om.engine
    with Session(engine) as s:
        rec = s.get(Conversation, conv_id)
        if rec is None:
            raise HTTPException(404, "not found")
        rec.archived = True
        s.commit()
    return {"ok": True}


@router.get("/{conv_id}/messages")
async def list_messages(conv_id: str, request: Request) -> list[dict]:
    engine = request.app.state.om.engine
    with Session(engine) as s:
        rows = s.exec(select(Message).where(Message.conv_id == conv_id)
                       .order_by(Message.id)).all()  # type: ignore[arg-type]
    return [{"id": r.id, "role": r.role, "content": r.content,
             "thinking": r.thinking, "created_at": r.created_at} for r in rows]
