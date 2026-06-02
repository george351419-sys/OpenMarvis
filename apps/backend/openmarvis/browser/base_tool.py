from __future__ import annotations

from ..tools.base import Tool, ToolContext
from .pool import BrowserPool


class BrowserToolBase(Tool):
    """Common base for browser tools — holds reference to BrowserPool.

    Sub-classes implement execute(args, ctx); call `await self._page(ctx)`
    to get a Playwright page bound to ctx.conv_id.
    """

    available_to = ("browser-agent",)

    def __init__(self, pool: BrowserPool):
        self.pool = pool

    async def _page(self, ctx: ToolContext):
        return await self.pool.get_page(conv_id=ctx.conv_id)
