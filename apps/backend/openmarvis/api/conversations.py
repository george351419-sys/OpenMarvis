from __future__ import annotations

import time

import ulid
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session, func, select

from ..store.models import (
    AuditLog,
    Conversation,
    MemoryEntry,
    Message,
    SubAgentRecord,
    WriteAudit,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

# 跟 conv_id 绑定的表（不含 Schedule —— Schedule 是定时任务声明，
# 即使 origin conv 被删，定时任务本身可能还活着 / 应由 cancel_schedule 单独清）。
_CONV_BOUND_TABLES = (
    (Message, "conv_id"),
    (MemoryEntry, "conv_id"),
    (SubAgentRecord, "conv_id"),
    (WriteAudit, "conv_id"),
    (AuditLog, "conv_id"),
)


def _purge_conv(session: Session, conv_id: str) -> dict[str, int]:
    """硬删一个 conv，连同关联的所有 row。返回各表删除条数。返回时 session
    尚未 commit；调用方负责 commit。"""
    counts: dict[str, int] = {}
    for model, fkcol in _CONV_BOUND_TABLES:
        rows = session.exec(
            select(model).where(getattr(model, fkcol) == conv_id)
        ).all()
        for r in rows:
            session.delete(r)
        counts[model.__name__] = len(rows)
    # 文件索引 / chunk 索引也清掉（FTS5 虚拟表，不归 SQLModel 管）
    for table in ("file_index_fts", "file_index_meta",
                   "chunk_index_fts", "chunk_index_meta"):
        # 缺表也无所谓 —— init_db 顺序保证它们都存在
        try:
            res = session.execute(
                text(f"DELETE FROM {table} WHERE conv_id=:c"),
                {"c": conv_id},
            )
            counts[table] = int(getattr(res, "rowcount", 0) or 0)
        except Exception:  # noqa: BLE001
            counts[table] = 0
    # 最后删 Conversation 本身
    rec = session.get(Conversation, conv_id)
    if rec is not None:
        session.delete(rec)
        counts["Conversation"] = 1
    else:
        counts["Conversation"] = 0
    return counts


class CreateConvRequest(BaseModel):
    title: str = ""


class PatchConvRequest(BaseModel):
    title: str


@router.patch("/{conv_id}")
async def patch_conv(conv_id: str, req: PatchConvRequest, request: Request) -> dict:
    engine = request.app.state.om.engine
    with Session(engine) as s:
        rec = s.get(Conversation, conv_id)
        if rec is None:
            raise HTTPException(404, "not found")
        rec.title = req.title
        rec.updated_at = int(time.time())
        s.commit()
    return {"id": conv_id, "title": req.title}


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


@router.post("/{conv_id}/purge")
async def purge_conv(conv_id: str, request: Request) -> dict:
    """硬删 conv：从 DB 里彻底移除（含所有 messages / memory / sub-agent
    记录 / audit / FTS 索引）。和 DELETE（软归档）不同，purge 之后**无法恢复**。
    """
    engine = request.app.state.om.engine
    with Session(engine) as s:
        rec = s.get(Conversation, conv_id)
        if rec is None:
            raise HTTPException(404, "conversation not found")
        counts = _purge_conv(s, conv_id)
        s.commit()
    return {"ok": True, "purged": counts}


class CleanupRequest(BaseModel):
    empty_title: bool = False     # 只删 title == ""
    min_age_days: int = 0          # 仅 updated_at < now - N*86400
    max_messages: int = -1         # 仅 messages 数 ≤ N；-1 = 不限
    include_archived: bool = True  # 是否含已 archive 的
    dry_run: bool = True           # True 时只统计不删；默认安全


@router.post("/cleanup")
async def cleanup_conversations(req: CleanupRequest, request: Request) -> dict:
    """按 filter 批量 purge（默认 dry_run）。

    用于清理你 sidebar 里几百个临时测试 conv。所有 filter 同时生效（AND）。
    """
    engine = request.app.state.om.engine
    now = int(time.time())
    cutoff = now - req.min_age_days * 86400 if req.min_age_days > 0 else now + 1
    with Session(engine) as s:
        # 先按 Conversation 元数据筛
        q = select(Conversation)
        if not req.include_archived:
            q = q.where(Conversation.archived == False)            # noqa: E712
        if req.empty_title:
            # 空标题或仅含纯空白 / 单字符（"t" / "" / " "）
            q = q.where(func.length(func.trim(Conversation.title)) <= 1)
        if req.min_age_days > 0:
            q = q.where(Conversation.updated_at < cutoff)
        candidates = list(s.exec(q).all())

        # max_messages 需要二次过滤（count 子查询太啰嗦了；几百条数据集没必要）
        if req.max_messages >= 0:
            filtered = []
            for c in candidates:
                n = s.exec(
                    select(func.count()).select_from(Message)        # type: ignore[arg-type]
                    .where(Message.conv_id == c.id)
                ).first() or 0
                if int(n) <= req.max_messages:
                    filtered.append(c)
            candidates = filtered

        if req.dry_run:
            return {
                "dry_run": True,
                "would_purge": len(candidates),
                "sample_ids": [c.id for c in candidates[:10]],
            }

        total_counts: dict[str, int] = {}
        for c in candidates:
            counts = _purge_conv(s, c.id)
            for k, v in counts.items():
                total_counts[k] = total_counts.get(k, 0) + v
        s.commit()
        return {
            "dry_run": False,
            "purged": len(candidates),
            "by_table": total_counts,
        }
