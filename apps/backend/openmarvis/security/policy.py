from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

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


def _import_guards():
    from .cmd_guard import CmdGuard
    from .credential_guard import CredentialGuard
    from .path_guard import PathGuard
    return PathGuard, CmdGuard, CredentialGuard


class SecurityGate:
    """组合 PathGuard / CmdGuard / CredentialGuard 决策。"""

    def __init__(self, workspace, extra_blocklist: list[str] | None = None):
        pg_cls, cg_cls, cr_cls = _import_guards()
        self.path_guard = pg_cls(workspace=workspace, extra_blocklist=extra_blocklist)
        self.cmd_guard = cg_cls()
        self.credential_guard = cr_cls()

    def _dynamic_decision(self, tool, args: dict[str, Any]) -> Decision:
        """Evaluate dynamic risk via tool.assess_risk and return a Decision."""
        try:
            parsed = tool.args_model.model_validate(args)
            ra = tool.assess_risk(parsed, ctx=None)
        except Exception:
            ra = type("RA", (), {"level": tool.risk_level, "reasons": []})()
        level_to_action: dict[str, Action] = {
            "low": "allow", "medium": "confirm", "high": "confirm",
        }
        action: Action = level_to_action.get(ra.level, "allow")
        return Decision(
            action=action,
            reason="; ".join(ra.reasons) or f"{tool.name} risk={ra.level}",
            details={"dynamic_reasons": list(ra.reasons), "tool": tool.name},
        )

    def _static_decisions(self, tool, args: dict[str, Any]) -> list[Decision]:
        """Run path / cmd / credential guards and return decisions."""
        decisions: list[Decision] = []
        path_fields = ("file_path", "path", "src", "dst", "target")
        for f in path_fields:
            v = args.get(f)
            if isinstance(v, str):
                decisions.append(self.path_guard.check_path(v))
        if "file_paths" in args and isinstance(args["file_paths"], list):
            for v in args["file_paths"]:
                decisions.append(self.path_guard.check_path(v))
        if "command" in args and isinstance(args["command"], str):
            if tool is None or not getattr(tool, "skip_cmd_guard", False):
                decisions.append(self.cmd_guard.check_command(args["command"]))
            decisions.append(self.credential_guard.scan(args["command"]))
        if "code" in args and isinstance(args["code"], str):
            decisions.append(self.credential_guard.scan(args["code"]))
        for v in args.values():
            if isinstance(v, str):
                decisions.append(self.credential_guard.scan(v))
        return decisions

    def check(self, *, tool=None, tool_name: str = "",
              args: dict[str, Any] | None = None) -> Decision:
        args = args or {}
        decisions = self._static_decisions(tool, args)
        if tool is not None:
            decisions.append(self._dynamic_decision(tool, args))
        return aggregate(decisions)


@dataclass
class RiskAssessment:
    level: str = "low"        # low / medium / high
    reasons: list[str] = field(default_factory=list)
