from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, Field

from ..tools.base import ToolContext, ToolResult
from .base_tool import BrowserToolBase


def _host_allowed(url: str, allowed_domains: list[str]) -> bool:
    if not allowed_domains:
        return True
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in allowed_domains)


# ---------- navigate ----------

class NavigateArgs(BaseModel):
    url: str = Field(description="要打开的 URL")


class NavigateTool(BrowserToolBase):
    name = "navigate"
    description = "在共享浏览器窗口里打开 URL，等待 networkidle"
    args_model = NavigateArgs
    risk_level = "low"

    async def execute(self, args: NavigateArgs, ctx: ToolContext) -> ToolResult:
        if not _host_allowed(args.url, self.pool.settings.allowed_domains):
            return ToolResult(error=f"domain_blocked: {args.url}")
        page = await self._page(ctx)
        try:
            await page.goto(args.url, wait_until="networkidle")
            return ToolResult(content=f"已导航到 {args.url}")
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"page_load_timeout: {args.url} ({e})")


# ---------- current_url ----------

class CurrentUrlArgs(BaseModel):
    pass


class CurrentUrlTool(BrowserToolBase):
    name = "current_url"
    description = "返回当前浏览器页面的 URL"
    args_model = CurrentUrlArgs
    risk_level = "low"

    async def execute(self, args, ctx: ToolContext) -> ToolResult:
        page = await self._page(ctx)
        return ToolResult(content=str(page.url))


# ---------- go_back ----------

class GoBackArgs(BaseModel):
    pass


class GoBackTool(BrowserToolBase):
    name = "go_back"
    description = "浏览器后退一步"
    args_model = GoBackArgs
    risk_level = "low"

    async def execute(self, args, ctx: ToolContext) -> ToolResult:
        page = await self._page(ctx)
        await page.go_back()
        return ToolResult(content="已后退")
