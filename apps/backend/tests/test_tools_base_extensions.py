from pydantic import BaseModel

from openmarvis.security.policy import RiskAssessment
from openmarvis.tools.base import Tool, ToolResult


class DummyArgs(BaseModel):
    x: int = 0


class NoSkipTool(Tool):
    name = "no_skip"
    description = "default skip_cmd_guard"
    args_model = DummyArgs
    risk_level = "low"
    available_to = ("agent",)

    async def execute(self, args, ctx):  # pragma: no cover
        return ToolResult(content="x")


class SkipTool(Tool):
    name = "skip"
    description = "set skip_cmd_guard True"
    args_model = DummyArgs
    risk_level = "low"
    available_to = ("agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):  # pragma: no cover
        return ToolResult(content="x")


class DynamicTool(Tool):
    name = "dyn"
    description = "dynamic risk via assess_risk"
    args_model = DummyArgs
    risk_level = "medium"
    available_to = ("agent",)

    def assess_risk(self, args, ctx):
        if args.x > 9000:
            return RiskAssessment(level="high", reasons=["x too big"])
        return RiskAssessment(level=self.risk_level, reasons=[])


def test_default_skip_cmd_guard_is_false():
    assert NoSkipTool.skip_cmd_guard is False


def test_skip_cmd_guard_class_override():
    assert SkipTool.skip_cmd_guard is True


def test_default_assess_risk_returns_class_level():
    tool = NoSkipTool()
    r = tool.assess_risk(DummyArgs(x=1), ctx=None)
    assert r.level == "low"
    assert r.reasons == []


def test_dynamic_assess_risk_upgrades():
    tool = DynamicTool()
    low = tool.assess_risk(DummyArgs(x=1), ctx=None)
    high = tool.assess_risk(DummyArgs(x=99999), ctx=None)
    assert low.level == "medium"
    assert high.level == "high"
    assert "too big" in high.reasons[0]
