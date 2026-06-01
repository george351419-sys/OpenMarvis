from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

SSE_EVENTS = SimpleNamespace(
    THINKING_DELTA="thinking_delta",
    CONTENT_DELTA="content_delta",
    TOOL_CALL_START="tool_call_start",
    TOOL_CALL_RESULT="tool_call_result",
    CARD="card",
    ASK_USER="ask_user",
    SUB_AGENT_START="sub_agent_start",
    SUB_AGENT_END="sub_agent_end",
    WARNING="warning",
    ERROR="error",
    DONE="done",
)


@dataclass
class SSEEvent:
    event: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        return {"event": self.event, "data": json.dumps(self.data, ensure_ascii=False)}
