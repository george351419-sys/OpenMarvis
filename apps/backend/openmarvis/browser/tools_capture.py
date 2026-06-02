from __future__ import annotations

import ulid
from pydantic import BaseModel, Field

from ..tools.base import Card, ToolContext, ToolResult
from .base_tool import BrowserToolBase


class ScreenshotArgs(BaseModel):
    full_page: bool = Field(default=False)
    selector: str | None = Field(default=None,
                                   description="若提供则只截取该元素")


class ScreenshotTool(BrowserToolBase):
    name = "screenshot"
    description = "截图，保存到 workspace/temp/，返回 mv-image-gallery 卡片"
    args_model = ScreenshotArgs
    risk_level = "low"

    async def execute(self, args: ScreenshotArgs, ctx: ToolContext) -> ToolResult:
        page = await self._page(ctx)
        fname = f"screenshot_{ulid.new().str.lower()}.png"
        path = ctx.workspace.temp_dir / fname
        try:
            if args.selector:
                await page.locator(args.selector).first.screenshot(path=str(path))
            else:
                await page.screenshot(path=str(path), full_page=args.full_page)
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"screenshot_failed: {e}")
        body = f"[{fname}](<{path}>)"
        return ToolResult(
            content=f"已截图: {path}",
            cards=[Card(type="mv-image-gallery", payload=body)],
        )
