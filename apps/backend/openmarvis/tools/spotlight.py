from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from .base import Card, Tool, ToolContext, ToolResult

KIND_MAP = {
    "pdf": "kind:pdf",
    "image": "kind:image",
    "audio": "kind:audio",
    "video": "kind:movie",
    "code": "kMDItemContentType == 'public.source-code'",
    "text": "kind:text",
    "word": "kind:words",
    "excel": "kind:numbers",
    "ppt": "kind:presentation",
}


class SpotlightArgs(BaseModel):
    query: str = Field(description="mdfind 查询语法")
    max_results: int = Field(default=50)
    onlyin: str | None = Field(default=None)
    kind: str | None = Field(default=None)


class SpotlightTool(Tool):
    name = "search_files_spotlight"
    description = (
        "用 macOS Spotlight (mdfind) 快速搜索本地文件。"
        "支持 query 元数据语法 + kind 简写（pdf/image/code/...） + onlyin 限定目录。"
    )
    args_model = SpotlightArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    async def execute(self, args: SpotlightArgs, ctx: ToolContext) -> ToolResult:
        cmd = ["mdfind"]
        if args.onlyin:
            decision = ctx.security.path_guard.check_path(args.onlyin)
            if decision.action == "block":
                return ToolResult(error=f"risk_blocked: {decision.reason}")
            cmd += ["-onlyin", args.onlyin]
        query = args.query
        if args.kind and args.kind in KIND_MAP:
            query = f"{KIND_MAP[args.kind]} {query}"
        cmd.append(query)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        except TimeoutError:
            return ToolResult(error="mdfind_timeout")
        hits = [
            p
            for p in (out or b"").decode("utf-8", errors="replace").splitlines()
            if p
        ][: args.max_results]
        body = "\n".join(f"[{Path(p).name}](<{p}>)" for p in hits) or "（无匹配）"
        return ToolResult(
            content=f"Spotlight 找到 {len(hits)} 项",
            cards=[Card(type="mv-file-list", payload=body)] if hits else [],
        )
