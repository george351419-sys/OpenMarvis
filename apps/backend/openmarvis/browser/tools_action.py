from __future__ import annotations

from pydantic import BaseModel, Field

from ..tools.base import ToolContext, ToolResult
from .base_tool import BrowserToolBase


class ClickArgs(BaseModel):
    selector: str = Field(description="CSS / Playwright selector")
    nth: int = Field(default=0)


class ClickTool(BrowserToolBase):
    name = "click"
    description = "点击匹配的元素（默认第一个）"
    args_model = ClickArgs
    risk_level = "medium"

    async def execute(self, args: ClickArgs, ctx: ToolContext) -> ToolResult:
        page = await self._page(ctx)
        try:
            loc = page.locator(args.selector).first
            await loc.scroll_into_view_if_needed()
            await loc.click()
            return ToolResult(content=f"已点击 {args.selector}")
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"click_failed: {args.selector} ({e})")


class FillArgs(BaseModel):
    selector: str
    value: str


class FillTool(BrowserToolBase):
    name = "fill"
    description = "在元素中填入文本（自动 focus + 清空）"
    args_model = FillArgs
    risk_level = "medium"

    async def execute(self, args: FillArgs, ctx: ToolContext) -> ToolResult:
        page = await self._page(ctx)
        try:
            loc = page.locator(args.selector).first
            await loc.fill(args.value)
            return ToolResult(content=f"已填入 {args.selector}")
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"fill_failed: {args.selector} ({e})")


class SubmitFormArgs(BaseModel):
    form_selector: str | None = Field(default=None,
                                        description="form 元素 selector；为空则按回车")


class SubmitFormTool(BrowserToolBase):
    name = "submit_form"
    description = "提交表单（或回车）"
    args_model = SubmitFormArgs
    risk_level = "medium"

    async def execute(self, args: SubmitFormArgs, ctx: ToolContext) -> ToolResult:
        page = await self._page(ctx)
        if args.form_selector:
            try:
                await page.locator(args.form_selector).first.evaluate(
                    "(el) => el.submit()")
                return ToolResult(content="表单已提交")
            except Exception as e:  # noqa: BLE001
                return ToolResult(error=f"submit_failed: {e}")
        await page.keyboard.press("Enter")
        return ToolResult(content="已按回车")
