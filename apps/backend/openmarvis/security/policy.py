from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Action = Literal["allow", "confirm", "block"]


@dataclass
class Decision:
    action: Action
    reason: str = ""
    details: dict = field(default_factory=dict)

    @staticmethod
    def allow(reason: str = "") -> Decision:
        return Decision(action="allow", reason=reason)

    @staticmethod
    def confirm(reason: str, **details) -> Decision:
        return Decision(action="confirm", reason=reason, details=details)

    @staticmethod
    def block(reason: str, **details) -> Decision:
        return Decision(action="block", reason=reason, details=details)


def aggregate(decisions: list[Decision]) -> Decision:
    """Most restrictive wins: block > confirm > allow."""
    order = {"allow": 0, "confirm": 1, "block": 2}
    if not decisions:
        return Decision.allow()
    return max(decisions, key=lambda d: order[d.action])
