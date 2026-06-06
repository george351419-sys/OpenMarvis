"""ai_search — 深度联网搜索工具。

一次调用完成：多路搜索 → 抓取正文 → LLM 综合 → 返回 Markdown 报告。
与 web_search（只返回链接列表）的区别：ai_search 返回已综合的内容，
等价于 Marvis 的 ai_search 工具（search-agent Sub Agent 的轻量替代）。
"""
from __future__ import annotations

import asyncio
import html
import re

import httpx
from pydantic import BaseModel, Field

from .base import Tool, ToolContext, ToolResult

_BRIEF_GUARD = (
    "\n\n[输出约束] 只输出综合结论的 Markdown，不要铺垫和寒暄，"
    "不要重复原文链接，保持简洁。"
)


def _clean_html(text: str, max_len: int = 6000) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


async def _fetch_one(client: httpx.AsyncClient, url: str) -> str:
    try:
        resp = await client.get(url, timeout=10.0,
                                headers={"User-Agent": "OpenMarvis/0.1"},
                                follow_redirects=True)
        resp.raise_for_status()
        return _clean_html(resp.text)
    except Exception:
        return ""


class AiSearchArgs(BaseModel):
    query: str = Field(description="搜索问题（自然语言，中英文均可）")
    max_sources: int = Field(default=5, ge=1, le=10,
                             description="抓取并综合的最大页面数（默认 5）")
    language: str = Field(default="zh",
                          description="期望返回语言（zh/en，默认 zh）")


class AiSearchTool(Tool):
    name = "ai_search"
    description = (
        "深度联网搜索：自动多路搜索 + 抓取正文 + LLM 综合，一次调用返回完整 Markdown 报告。"
        "比 web_search（只返回链接列表）更强，适合需要真实内容的研究类问题。"
        "需配置 BRAVE_SEARCH_API_KEY。"
    )
    args_model = AiSearchArgs
    risk_level = "low"
    available_to = ("main", "file-agent", "search-agent")

    def __init__(self, api_key: str | None = None, llm=None):
        self.api_key = api_key
        self.llm = llm

    async def execute(self, args: AiSearchArgs, ctx: ToolContext) -> ToolResult:
        if not self.api_key:
            return ToolResult(error="ai_search 未配置 BRAVE_SEARCH_API_KEY")
        if self.llm is None:
            return ToolResult(error="ai_search 未配置 LLM 客户端")

        # Step 1: search
        headers = {"X-Subscription-Token": self.api_key, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers=headers,
                    params={"q": args.query, "count": args.max_sources * 2},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                return ToolResult(error=f"搜索请求失败: {e}")

        results = (data.get("web", {}) or {}).get("results", [])[:args.max_sources * 2]
        if not results:
            return ToolResult(content=f"未找到与 '{args.query}' 相关的网页")

        # Step 2: fetch top pages concurrently
        urls = [r.get("url", "") for r in results if r.get("url")][:args.max_sources]
        async with httpx.AsyncClient(timeout=15.0) as client:
            texts = await asyncio.gather(*[_fetch_one(client, u) for u in urls])

        # Step 3: build context
        snippets = []
        for i, (r, body) in enumerate(zip(results, texts)):
            title = r.get("title", "")
            url = r.get("url", "")
            content = body or r.get("description", "")
            if content:
                snippets.append(f"### 来源 {i+1}: {title}\nURL: {url}\n\n{content[:3000]}")

        if not snippets:
            titles = "\n".join(f"- {r.get('title','')} ({r.get('url','')})" for r in results[:5])
            return ToolResult(content=f"搜索到以下结果（无法抓取正文）：\n{titles}")

        ctx_text = "\n\n---\n\n".join(snippets)
        lang_hint = "请用中文回答" if args.language == "zh" else "Please answer in English"

        prompt = (
            f"以下是关于「{args.query}」的多个网页内容：\n\n"
            f"{ctx_text}\n\n"
            f"---\n请基于以上内容综合回答：{args.query}\n"
            f"{lang_hint}，用 Markdown 格式输出，包含关键结论和必要细节。"
            f"{_BRIEF_GUARD}"
        )

        # Step 4: synthesize
        try:
            answer = await self.llm.complete_sync(
                messages=[{"role": "user", "content": prompt}]
            )
        except Exception as e:
            # Fallback: return raw snippets
            answer = "\n\n".join(snippets[:3])
            return ToolResult(content=f"（综合失败: {e}，返回原始片段）\n\n{answer}")

        sources_md = "\n".join(
            f"{i+1}. [{r.get('title',r.get('url',''))}]({r.get('url','')})"
            for i, r in enumerate(results[:args.max_sources])
        )
        return ToolResult(content=f"{answer}\n\n---\n**来源**\n{sources_md}")
