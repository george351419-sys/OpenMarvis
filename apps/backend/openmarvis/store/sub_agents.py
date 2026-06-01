from __future__ import annotations

import json
import time
from typing import Any

from sqlmodel import Session

from .models import SubAgentRecord


class SubAgentStore:
    def __init__(self, engine):
        self.engine = engine

    async def save(self, **fields) -> None:
        now = int(time.time())
        fields.setdefault("created_at", now)
        if fields.get("status") == "completed":
            fields.setdefault("completed_at", now)
        with Session(self.engine) as s:
            existing = s.get(SubAgentRecord, fields["agent_id"])
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                s.add(SubAgentRecord(**fields))
            s.commit()

    async def get_full(self, *, agent_id: str, conv_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as s:
            rec = s.get(SubAgentRecord, agent_id)
            if rec is None or rec.conv_id != conv_id:
                return None
            return {
                "agent_id": rec.agent_id,
                "agent_name": rec.agent_name,
                "status": rec.status,
                "summary": rec.summary,
                "full_content": rec.full_content,
                "cards": json.loads(rec.cards_json) if rec.cards_json else [],
            }

    async def try_inherit(self, *, target_agent_name: str, source_id: str,
                          conv_id: str) -> list[dict] | None:
        with Session(self.engine) as s:
            rec = s.get(SubAgentRecord, source_id)
            if rec is None:
                return None
            if rec.conv_id != conv_id:
                return None
            if rec.agent_name != target_agent_name:
                return None
            if rec.status != "completed":
                return None
            try:
                return json.loads(rec.messages_json) or []
            except json.JSONDecodeError:
                return None
