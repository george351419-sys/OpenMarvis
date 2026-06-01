from __future__ import annotations

import html
import re

import httpx
from pydantic import BaseModel, Field

from .base import Tool, ToolContext, ToolResult

# ---------- web_search ----------

class WebSearchArgs(BaseModel):
    query: str
    max_results: int = Field(default=10)


class WebSearchTool(Tool):
    name = "web_search"
    description = "轻量网页搜索，返回标题/链接/摘要列表。"
    args_model = WebSearchArgs
    risk_level = "low"
    available_to = ("main", "search-agent")

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    async def execute(self, args: WebSearchArgs, ctx: ToolContext) -> ToolResult:
        if not self.api_key:
            return ToolResult(error="web_search 未配置 BRAVE_SEARCH_API_KEY")
        headers = {"X-Subscription-Token": self.api_key, "Accept": "application/json"}
        params = {"q": args.query, "count": args.max_results}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers, params=params,
            )
            resp.raise_for_status()
            data = resp.json()
        items = (data.get("web", {}) or {}).get("results", [])[: args.max_results]
        lines = [f"- [{it.get('title','')}]({it.get('url','')}) — {it.get('description','')}"
                 for it in items]
        return ToolResult(content="\n".join(lines) or "（无结果）")


# ---------- web_fetch ----------

class WebFetchArgs(BaseModel):
    url: str
    as_markdown: bool = True
    max_content_length: int = Field(default=200_000)


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "抓取网页正文（Markdown 或纯文本）。"
    args_model = WebFetchArgs
    risk_level = "low"
    available_to = ("main", "search-agent")

    async def execute(self, args: WebFetchArgs, ctx: ToolContext) -> ToolResult:
        if not args.url.startswith(("http://", "https://")):
            return ToolResult(error="URL 必须以 http:// 或 https:// 开头")
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(args.url, headers={"User-Agent": "OpenMarvis/0.1"})
            resp.raise_for_status()
            text = resp.text
        text = re.sub(r"<script[\s\S]*?</script>", "", text)
        text = re.sub(r"<style[\s\S]*?</style>", "", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > args.max_content_length:
            text = text[: args.max_content_length] + "...[truncated]"
        return ToolResult(content=text)
