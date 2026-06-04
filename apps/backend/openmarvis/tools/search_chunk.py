"""search_chunk: 跨文件按段落定位。

vs search_file 的差别：
- search_file 返回整文件（哪个文件命中）
- search_chunk 返回**具体段落**（文件里哪一段命中）

适合场景：长 PDF / 论文 / 报告里精准找"提到 X 的那段话"。
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ..store.chunk_index import index_directory_chunks, search_chunks
from .base import Card, Tool, ToolContext, ToolResult


class SearchChunkArgs(BaseModel):
    query: str = Field(description="查询关键词，trigram 索引，中英都行")
    limit: int = Field(default=10, ge=1, le=50,
                        description="返回上限（每条是一个段落）")
    reindex_root: str | None = Field(
        default=None,
        description=(
            "可选：先把此目录按段重新索引再查。文件第一次用时需传，"
            "之后增量自动跳过未变化的文件。"
        ),
    )


class SearchChunkTool(Tool):
    name = "search_chunk"
    description = (
        "在文件**段落级**做 FTS5 全文搜索。返回命中段落的完整文本 + "
        "高亮片段 + 文件路径 + 段落序号（chunk_idx）。"
        "适合在长文档里精准定位'提到 X 的那段'。"
        "如果工作区还没建过 chunk 索引，传 reindex_root=<目录> 让本工具先索引再查。"
    )
    args_model = SearchChunkArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    def __init__(self, engine):
        self.engine = engine

    async def execute(self, args: SearchChunkArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(
            tool=self, tool_name=self.name,
            args={"path": args.reindex_root} if args.reindex_root else {},
        )
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        preamble = ""
        if args.reindex_root:
            root = Path(args.reindex_root).expanduser()
            if not root.is_dir():
                return ToolResult(error=f"不是目录: {root}")
            stats = index_directory_chunks(self.engine, conv_id=ctx.conv_id,
                                              root=root)
            preamble = (
                f"[已索引 {root}: {stats['files']} 个文件, "
                f"{stats['chunks']} 段; 跳过 {stats['skipped']} 个未变化]\n\n"
            )
        try:
            hits = search_chunks(self.engine, conv_id=ctx.conv_id,
                                    query=args.query, limit=args.limit)
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"FTS chunk 查询失败: {e}")
        if not hits:
            return ToolResult(
                content=preamble + f"未找到匹配 '{args.query}' 的段落",
            )
        # 每条命中：文件名 + 段号 + 高亮 + 完整 chunk
        body_parts = []
        seen_files: set[str] = set()
        for h in hits:
            name = Path(h.file_path).name
            body_parts.append(
                f"### {name} · 段 {h.chunk_idx}\n"
                f"`{h.file_path}`\n\n"
                f"**片段**：{h.snippet}\n\n"
                f"**全文**：\n{h.chunk_text}"
            )
            seen_files.add(h.file_path)
        cards = []
        if seen_files:
            card_lines = "\n".join(
                f"[{Path(p).name}](<{p}>)" for p in sorted(seen_files)
            )
            cards = [Card(type="mv-file-list", payload=card_lines)]
        content = preamble + f"找到 {len(hits)} 个匹配段落\n\n" + "\n\n---\n\n".join(body_parts)
        return ToolResult(content=content, cards=cards)
