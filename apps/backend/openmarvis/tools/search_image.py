"""search_image — 图片语义检索工具。

通过多路查询 + RRF 融合排序，在已索引文件中定位图片。
与 image-search Skill 的关系：
  - 该工具提供底层检索能力（BM25 + 路径 glob + 去重）
  - image-search Skill 在此基础上加了 analyze_image 视觉验证二阶段
  - 推荐路由：视觉语义搜图 → use_skill(image-search)；
             快速按文件名/元数据搜图 → search_image 直调
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from pydantic import BaseModel, Field

from ..store.file_index import search
from .base import Card, Tool, ToolContext, ToolResult

_IMAGE_EXTS = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
    ".heic", ".heif", ".tiff", ".tif", ".svg", ".ico",
})

_THUMBNAIL_SUFFIXES = ("_thumb", "_thumbnail", "_small", "_preview",
                       "-thumb", "-thumbnail", "-small", "-preview")


def _is_image(path: str) -> bool:
    return Path(path).suffix.lower() in _IMAGE_EXTS


def _is_thumbnail(name: str) -> bool:
    stem = Path(name).stem.lower()
    return any(stem.endswith(s) for s in _THUMBNAIL_SUFFIXES)


def _rrf_merge(result_lists: list[list[str]], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion — merge multiple ranked lists into one."""
    scores: dict[str, float] = {}
    for ranked in result_lists:
        for rank, item in enumerate(ranked):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda x: -scores[x])


def _glob_images(root: Path, pattern: str, limit: int) -> list[str]:
    """Glob-based image file search."""
    results: list[str] = []
    try:
        for p in root.rglob(pattern):
            if p.is_file() and _is_image(str(p)):
                results.append(str(p))
                if len(results) >= limit * 3:
                    break
    except PermissionError:
        pass
    return results


class SearchImageArgs(BaseModel):
    queries: list[str] = Field(
        description=(
            "语义描述列表（多角度查询），如 ['风景照', 'landscape', '山水']。"
            "每个 query 独立检索后 RRF 融合，提高召回率。至少 1 个。"
        ),
        min_length=1,
    )
    search_root: str | None = Field(
        default=None,
        description="搜索根目录绝对路径。不传则在工作区内搜索。",
    )
    sql: str | None = Field(
        default=None,
        description=(
            "可选 SQL 元数据筛选，如 \"name LIKE '%.jpg' AND path LIKE '%2025%'\"。"
            "作为附加过滤条件，在 FTS 结果之后应用。"
        ),
    )
    file_ids: list[str] | None = Field(
        default=None,
        description="可选：只在这些文件路径列表中搜索（白名单过滤）。",
    )
    limit: int = Field(default=20, ge=1, le=200, description="最终返回结果上限。")
    include_thumbnails: bool = Field(
        default=False,
        description="是否包含缩略图（文件名含 _thumb/_small 等后缀）。默认排除。",
    )


class SearchImageTool(Tool):
    name = "search_image"
    description = (
        "图片语义检索工具。多路 BM25 查询 + RRF 融合排序，返回去重后的图片路径列表。"
        "⚠️ 该工具只负责检索，不做视觉验证。需要高精度视觉验证时用 use_skill(image-search)。"
        "适用场景：按文件名/路径关键词找图、快速召回候选图片集合。"
    )
    args_model = SearchImageArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    def __init__(self, engine=None):
        self.engine = engine

    async def execute(self, args: SearchImageArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name,
                                      args={"path": args.search_root or ""})
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")

        root = Path(args.search_root).expanduser() if args.search_root else ctx.workspace.root
        if not root.exists():
            return ToolResult(error=f"搜索根目录不存在: {root}")

        # Multi-query BM25 retrieval
        all_ranked: list[list[str]] = []
        if self.engine is not None:
            for q in args.queries:
                hits = search(self.engine, conv_id=ctx.conv_id,
                              query=q, field="any", limit=args.limit * 3)
                image_hits = [h.path for h in hits if _is_image(h.path)]
                if image_hits:
                    all_ranked.append(image_hits)

        # Glob fallback (for queries that look like filename patterns)
        for q in args.queries:
            safe = re.sub(r"[^\w\-\.\*\?\[\]]", "*", q)
            if "*" in safe or "." in safe:
                glob_hits = _glob_images(root, safe, args.limit)
            else:
                glob_hits = _glob_images(root, f"*{q}*", args.limit)
            if glob_hits:
                all_ranked.append(glob_hits)

        if not all_ranked:
            # Last resort: list all images in root
            all_images = _glob_images(root, "*", args.limit * 2)
            if not all_images:
                return ToolResult(content=f"在 `{root}` 下未找到任何图片文件")
            all_ranked.append(all_images)

        # RRF merge
        merged = _rrf_merge(all_ranked)

        # Filter: images only, optionally exclude thumbnails, apply whitelist
        filtered: list[str] = []
        seen_canonical: set[str] = set()
        for p in merged:
            if not _is_image(p):
                continue
            if not args.include_thumbnails and _is_thumbnail(p):
                continue
            if args.file_ids and p not in args.file_ids:
                continue
            # Deduplicate by canonical path
            canon = str(Path(p).resolve())
            if canon in seen_canonical:
                continue
            seen_canonical.add(canon)
            filtered.append(p)
            if len(filtered) >= args.limit:
                break

        if not filtered:
            return ToolResult(content=f"未找到与 {args.queries} 相关的图片")

        card_lines = [f"[{Path(p).name}](<{p}>)" for p in filtered]
        summary_lines = [f"- `{p}`" for p in filtered[:10]]
        if len(filtered) > 10:
            summary_lines.append(f"  …共 {len(filtered)} 张")

        return ToolResult(
            content=(
                f"找到 {len(filtered)} 张图片（查询: {args.queries}）\n\n"
                + "\n".join(summary_lines)
            ),
            cards=[Card(type="mv-image-gallery", payload="\n".join(card_lines))],
        )
