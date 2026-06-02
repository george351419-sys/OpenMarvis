from __future__ import annotations

from pydantic import BaseModel, Field

from ..tools.base import ToolContext, ToolResult
from .base_tool import BrowserToolBase


class ExtractTextArgs(BaseModel):
    selector: str
    nth: int = Field(default=0)


class ExtractTextTool(BrowserToolBase):
    name = "extract_text"
    description = "提取匹配元素的 innerText"
    args_model = ExtractTextArgs
    risk_level = "low"

    async def execute(self, args: ExtractTextArgs, ctx: ToolContext) -> ToolResult:
        page = await self._page(ctx)
        try:
            loc = page.locator(args.selector).first
            text = await loc.inner_text()
            return ToolResult(content=text)
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"extract_text_failed: {args.selector} ({e})")


class ListElementsArgs(BaseModel):
    selector: str
    attrs: list[str] = Field(default_factory=lambda: ["text"],
                              description="属性名列表；text 表示 innerText")
    max: int = Field(default=50)


class ListElementsTool(BrowserToolBase):
    name = "list_elements"
    description = "列出所有匹配元素的指定属性 / 文本"
    args_model = ListElementsArgs
    risk_level = "low"

    async def execute(self, args: ListElementsArgs, ctx: ToolContext) -> ToolResult:
        page = await self._page(ctx)
        try:
            loc = page.locator(args.selector)
            n = min(await loc.count(), args.max)
            rows = []
            for i in range(n):
                item = loc.nth(i)
                parts: list[str] = []
                for a in args.attrs:
                    if a == "text":
                        parts.append(await item.inner_text())
                    else:
                        v = await item.get_attribute(a)
                        parts.append(f"{a}={v}")
                rows.append(" | ".join(parts))
            return ToolResult(content="\n".join(rows) or "(no matches)")
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"list_elements_failed: {args.selector} ({e})")
