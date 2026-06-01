from __future__ import annotations

import time
from dataclasses import dataclass

import ulid
from sqlmodel import Session, select

from ..store.models import MemoryEntry


@dataclass
class MemoryRecord:
    id: str
    conv_id: str
    content: str
    created_at: int


class MemoryStore:
    def __init__(self, engine):
        self.engine = engine

    async def put(self, *, conv_id: str, content: str) -> str:
        mid = f"memory_{ulid.new().str.lower()}"
        with Session(self.engine) as s:
            s.add(MemoryEntry(id=mid, conv_id=conv_id, content=content, created_at=int(time.time())))
            s.commit()
        return mid

    async def fetch(self, memory_ids: list[str], *, conv_id: str) -> list[MemoryRecord]:
        if not memory_ids:
            return []
        with Session(self.engine) as s:
            rows = s.exec(
                select(MemoryEntry).where(
                    MemoryEntry.id.in_(memory_ids),
                    MemoryEntry.conv_id == conv_id,
                )
            ).all()
        return [
            MemoryRecord(id=r.id, conv_id=r.conv_id, content=r.content, created_at=r.created_at)
            for r in rows
        ]

    @staticmethod
    def summarize_preview(content: str, max_chars: int = 400) -> str:
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "..."
