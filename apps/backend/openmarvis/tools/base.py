from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import BaseModel

from ..security.policy import RiskAssessment


@dataclass
class Card:
    type: str
    payload: str


@dataclass
class ToolResult:
    content: str = ""
    memory_id: str | None = None
    cards: list[Card] = field(default_factory=list)
    error: str | None = None


@dataclass
class ToolContext:
    conv_id: str
    agent_id: str
    workspace: Any                # Workspace
    memory_store: Any             # MemoryStore
    security: Any                 # SecurityGate
    event_sink: Any               # EventSink
    user_settings: Any            # Settings


class Tool:
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    args_model: ClassVar[type[BaseModel]]
    risk_level: ClassVar[str] = "low"     # low / medium / high
    available_to: ClassVar[Iterable[str]] = ()
    skip_cmd_guard: ClassVar[bool] = False

    async def execute(self, args: BaseModel, ctx: ToolContext) -> ToolResult:  # pragma: no cover
        raise NotImplementedError

    def assess_risk(self, args: BaseModel, ctx: ToolContext | None) -> RiskAssessment:
        return RiskAssessment(level=self.risk_level, reasons=[])

    def anthropic_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.args_model.model_json_schema(),
        }
