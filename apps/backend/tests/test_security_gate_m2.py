from pydantic import BaseModel

from openmarvis.security.policy import RiskAssessment, SecurityGate
from openmarvis.tools.base import Tool, ToolResult
from openmarvis.workspace.manager import Workspace


class Args(BaseModel):
    command: str = ""
    script: str = ""


class CmdSkippingTool(Tool):
    name = "osascript_volume_set"
    description = "computer agent tool that bypasses cmd guard"
    args_model = Args
    risk_level = "medium"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):  # pragma: no cover
        return ToolResult(content="ok")


class JsEvalTool(Tool):
    name = "evaluate"
    description = "browser evaluate with dynamic risk"
    args_model = Args
    risk_level = "medium"
    available_to = ("browser-agent",)

    def assess_risk(self, args, ctx):
        risky = ("document.cookie", "localStorage", "sessionStorage", "fetch(", "XMLHttpRequest")
        if any(k in (args.script or "") for k in risky):
            return RiskAssessment(level="high", reasons=["JS 可能访问 cookie/storage 或外发请求"])
        return RiskAssessment(level=self.risk_level, reasons=[])

    async def execute(self, args, ctx):  # pragma: no cover
        return ToolResult(content="ok")


def make_ws(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    return ws


def test_skip_cmd_guard_bypasses_cmd_inspection(tmp_path):
    ws = make_ws(tmp_path)
    gate = SecurityGate(workspace=ws)
    tool = CmdSkippingTool()
    decision = gate.check(tool=tool,
                          tool_name=tool.name,
                          args={"command": "rm -rf /"})
    # 即使 command 命中 CmdGuard 黑名单，skip_cmd_guard 让它通过 CmdGuard 阶段；
    # 仍可能由 PathGuard/CredentialGuard 触发别的判定。"rm -rf /" 不含路径关键字段，
    # 应当 allow（low）。
    assert decision.action == "allow"


def test_assess_risk_upgrades_block_for_cookie_read(tmp_path):
    ws = make_ws(tmp_path)
    gate = SecurityGate(workspace=ws)
    tool = JsEvalTool()
    decision = gate.check(tool=tool,
                          tool_name=tool.name,
                          args={"script": "return document.cookie"})
    assert decision.action in ("confirm", "block")
    assert any("cookie" in r for r in (decision.details.get("dynamic_reasons", []) or
                                        [decision.reason]))


def test_assess_risk_clean_script_stays_medium(tmp_path):
    ws = make_ws(tmp_path)
    gate = SecurityGate(workspace=ws)
    tool = JsEvalTool()
    decision = gate.check(tool=tool,
                          tool_name=tool.name,
                          args={"script": "return document.title"})
    # medium 在 normal 模式下 = confirm（AI 自主提议）；plan 中默认 normal
    assert decision.action == "confirm"
