"""search_file: SQLite FTS5 全文索引检索。

vs search_files（os.walk + glob 暴力扫描）：
- 索引化，大工作区查询毫秒级
- 支持中英文（trigram tokenizer）
- 含 BM25 排序与片段高亮

第一次用要先 `index_directory` 建索引（或调 search_file 时自动跑）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ..store.file_index import index_directory, search
from .base import Card, Tool, ToolContext, ToolResult


class SearchFileArgs(BaseModel):
    query: str = Field(description="查询关键词。支持中英文，trigram 索引。")
    field: Literal["content", "name", "path", "any"] = Field(
        default="content",
        description=(
            "content=正文（默认）；name=仅文件名；path=路径前缀；any=任意字段。"
        ),
    )
    limit: int = Field(default=20, ge=1, le=100, description="返回上限")
    reindex_root: str | None = Field(
        default=None,
        description=(
            "可选：先把此目录重新索引一遍再查（首次查或文件变更后用）。"
            "传 workspace 路径或子目录的绝对路径。"
        ),
    )


class SearchFileTool(Tool):
    name = "search_file"
    description = (
        "用 SQLite FTS5 索引搜索本地文件。比 search_files（os.walk）快很多，"
        "支持 BM25 排序、片段高亮、中文 trigram。"
        "field=content 搜正文（PDF/DOCX/MD/...），field=name 仅文件名。"
        "如果工作区还没建过索引，传 reindex_root=<目录> 让本工具先索引再查。"
    )
    args_model = SearchFileArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    def __init__(self, engine):
        self.engine = engine

    async def execute(self, args: SearchFileArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(
            tool=self, tool_name=self.name,
            args={"path": args.reindex_root} if args.reindex_root else {},
        )
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if args.reindex_root:
            root = Path(args.reindex_root).expanduser()
            if not root.is_dir():
                return ToolResult(error=f"不是目录: {root}")
            stats = index_directory(self.engine, conv_id=ctx.conv_id, root=root)
            preamble = (
                f"[已索引 {root}: 新增/更新 {stats['indexed']}, "
                f"跳过 {stats['skipped']} 个文件]\n\n"
            )
        else:
            preamble = ""
        try:
            hits = search(self.engine, conv_id=ctx.conv_id,
                            query=args.query, field=args.field, limit=args.limit)
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"FTS 查询失败: {e}")
        if not hits:
            return ToolResult(content=preamble + f"未找到与 '{args.query}' 匹配的文件")
        body_lines = []
        card_lines = []
        for h in hits:
            body_lines.append(f"### {h.name}\n`{h.path}`\n\n{h.snippet}")
            card_lines.append(f"[{h.name}](<{h.path}>)")
        content = preamble + f"找到 {len(hits)} 个匹配\n\n" + "\n\n---\n\n".join(body_lines)
        return ToolResult(
            content=content,
            cards=[Card(type="mv-file-list", payload="\n".join(card_lines))],
        )
