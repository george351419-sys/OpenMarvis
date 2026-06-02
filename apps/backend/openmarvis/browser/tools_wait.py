from __future__ import annotations

from pydantic import BaseModel, Field

from ..tools.base import ToolContext, ToolResult
from .base_tool import BrowserToolBase


class WaitForSelectorArgs(BaseModel):
    selector: str
    timeout: int = Field(default=10000, description="毫秒")


class WaitForSelectorTool(BrowserToolBase):
    name = "wait_for_selector"
    description = "等待元素出现"
    args_model = WaitForSelectorArgs
    risk_level = "low"

    async def execute(self, args: WaitForSelectorArgs, ctx: ToolContext) -> ToolResult:
        page = await self._page(ctx)
        try:
            await page.wait_for_selector(args.selector, timeout=args.timeout)
            return ToolResult(content=f"已出现 {args.selector}")
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"wait_for_selector_failed: {args.selector} ({e})")
