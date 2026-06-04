from __future__ import annotations

import time
from dataclasses import dataclass

import ulid
from sqlmodel import Session, select

from ..store.models import MemoryEntry


USER_PREF_CONV_ID = "_global"   # 跨会话偏好的固定 conv_id


@dataclass
class MemoryRecord:
    id: str
    conv_id: str
    content: str
    created_at: int
    kind: str = "tool_result"


class MemoryStore:
    def __init__(self, engine):
        self.engine = engine

    async def put(self, *, conv_id: str, content: str,
                  kind: str = "tool_result") -> str:
        mid = f"memory_{ulid.new().str.lower()}"
        with Session(self.engine) as s:
            s.add(MemoryEntry(id=mid, conv_id=conv_id, content=content,
                               created_at=int(time.time()), kind=kind))
            s.commit()
        return mid

    async def fetch(self, memory_ids: list[str], *, conv_id: str) -> list[MemoryRecord]:
        if not memory_ids:
            return []
        with Session(self.engine) as s:
            rows = s.exec(
                select(MemoryEntry).where(
                    MemoryEntry.id.in_(memory_ids),                 # type: ignore[attr-defined]
                    MemoryEntry.conv_id == conv_id,
                )
            ).all()
        return [
            MemoryRecord(id=r.id, conv_id=r.conv_id, content=r.content,
                          created_at=r.created_at, kind=r.kind)
            for r in rows
        ]

    async def fetch_user_prefs(self, *, limit: int = 50) -> list[MemoryRecord]:
        """所有 kind='user_pref' 的偏好，按创建时间升序（旧的在前，方便阅读）。"""
        with Session(self.engine) as s:
            rows = s.exec(
                select(MemoryEntry)
                .where(MemoryEntry.kind == "user_pref")
                .where(MemoryEntry.conv_id == USER_PREF_CONV_ID)
                .order_by(MemoryEntry.created_at)                    # type: ignore[arg-type]
                .limit(limit)
            ).all()
        return [
            MemoryRecord(id=r.id, conv_id=r.conv_id, content=r.content,
                          created_at=r.created_at, kind=r.kind)
            for r in rows
        ]

    async def delete_user_pref(self, *, pref_id: str) -> bool:
        with Session(self.engine) as s:
            rec = s.get(MemoryEntry, pref_id)
            if rec is None or rec.kind != "user_pref":
                return False
            s.delete(rec)
            s.commit()
        return True

    @staticmethod
    def summarize_preview(content: str, max_chars: int = 400) -> str:
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "..."
