from __future__ import annotations

import json

from pydantic import BaseModel, Field

from ..security.policy import RiskAssessment
from ..tools.base import ToolContext, ToolResult
from .base_tool import BrowserToolBase

_RISKY_TOKENS = ("document.cookie", "localStorage", "sessionStorage",
                  "fetch(", "XMLHttpRequest")


class EvaluateArgs(BaseModel):
    script: str = Field(description="在页面上下文执行的 JS（function body 形式）")


class EvaluateTool(BrowserToolBase):
    name = "evaluate"
    description = "在页面上下文执行 JS，返回 JSON.stringify(result)。AI 自主提议时风险升级"
    args_model = EvaluateArgs
    risk_level = "medium"

    def assess_risk(self, args: EvaluateArgs, ctx) -> RiskAssessment:
        if any(t in args.script for t in _RISKY_TOKENS):
            return RiskAssessment(level="high",
                                   reasons=["JS 可能访问 cookie/storage 或外发请求"])
        return RiskAssessment(level=self.risk_level, reasons=[])

    async def execute(self, args: EvaluateArgs, ctx: ToolContext) -> ToolResult:
        page = await self._page(ctx)
        try:
            result = await page.evaluate(f"() => {{ {args.script} }}")
            return ToolResult(content=json.dumps(result, ensure_ascii=False, default=str))
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"evaluate_failed: {e}")
