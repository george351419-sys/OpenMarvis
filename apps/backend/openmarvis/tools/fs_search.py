"""fs_search_file / fs_search_content — ripgrep-based fallback search tools.

Used when index-based search_file has no results or the workspace is unindexed.
Requires `rg` (ripgrep) on PATH; falls back to `grep -r` if unavailable.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from .base import Card, Tool, ToolContext, ToolResult

_RG = shutil.which("rg")
_GREP = shutil.which("grep")


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 20) -> tuple[str, str, int]:
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd
    )
    return result.stdout, result.stderr, result.returncode


# ---------- fs_search_file ----------


class FsSearchFileArgs(BaseModel):
    pattern: str = Field(description="文件名 glob 或正则，如 '*.pdf'、'report*'、'202[45]*'")
    root: str = Field(description="搜索根目录的绝对路径")
    max_results: int = Field(default=50, ge=1, le=200)


class FsSearchFileTool(Tool):
    name = "fs_search_file"
    description = (
        "用 ripgrep 按文件名 glob 搜索文件（不看内容）。"
        "是 search_file / spotlight 的兜底：索引搜索无结果时用。"
        "pattern 示例：'*.pdf'、'合同*'、'invoice_2025*'。"
    )
    args_model = FsSearchFileArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    async def execute(self, args: FsSearchFileArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name,
                                      args={"path": args.root})
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        root = Path(args.root).expanduser()
        if not root.exists():
            return ToolResult(error=f"目录不存在: {root}")

        if _RG:
            cmd = ["rg", "--files", "--glob", args.pattern,
                   "--max-count", "1", str(root)]
            out, _err, _ = _run(cmd)
        else:
            cmd = ["find", str(root), "-name", args.pattern, "-type", "f"]
            out, _err, _ = _run(cmd)

        paths = [p.strip() for p in out.splitlines() if p.strip()][: args.max_results]
        if not paths:
            return ToolResult(content=f"未找到匹配 '{args.pattern}' 的文件")

        card_lines = [f"[{Path(p).name}](<{p}>)" for p in paths]
        return ToolResult(
            content=f"找到 {len(paths)} 个文件（glob: {args.pattern}）\n" +
                    "\n".join(f"- `{p}`" for p in paths),
            cards=[Card(type="mv-file-list", payload="\n".join(card_lines))],
        )


# ---------- fs_search_content ----------


class FsSearchContentArgs(BaseModel):
    pattern: str = Field(description="要在文件内容中搜索的正则或字面量字符串")
    root: str = Field(description="搜索根目录的绝对路径")
    file_glob: str = Field(
        default="*",
        description="限制搜索的文件类型，如 '*.py'、'*.md'。默认搜索所有文本文件。",
    )
    context_lines: int = Field(default=2, ge=0, le=10, description="匹配行前后的上下文行数")
    max_results: int = Field(default=30, ge=1, le=100)
    case_sensitive: bool = Field(default=False)


class FsSearchContentTool(Tool):
    name = "fs_search_content"
    description = (
        "用 ripgrep 在文件内容中搜索关键词或正则（全文 grep）。"
        "search_file（FTS 索引）无结果时的终极兜底。"
        "返回匹配行及上下文，附 mv-file-list 卡片。"
    )
    args_model = FsSearchContentArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    async def execute(self, args: FsSearchContentArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name,
                                      args={"path": args.root})
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        root = Path(args.root).expanduser()
        if not root.exists():
            return ToolResult(error=f"目录不存在: {root}")

        if _RG:
            cmd = [
                "rg", "--with-filename", "--line-number",
                f"--context={args.context_lines}",
                "--glob", args.file_glob,
                f"--max-count={args.max_results}",
            ]
            if not args.case_sensitive:
                cmd.append("--ignore-case")
            cmd += [args.pattern, str(root)]
        elif _GREP:
            cmd = [
                "grep", "-r", "--with-filename", "--line-number",
                f"--include={args.file_glob}",
                f"-C{args.context_lines}",
            ]
            if not args.case_sensitive:
                cmd.append("-i")
            cmd += [args.pattern, str(root)]
        else:
            return ToolResult(error="系统未安装 ripgrep 或 grep，无法执行内容搜索")

        out, _err, _ = _run(cmd, timeout=30)
        if not out.strip():
            return ToolResult(content=f"未找到包含 '{args.pattern}' 的文件")

        # Extract unique file paths for the card
        seen_files: dict[str, str] = {}
        for line in out.splitlines():
            if ":" in line and not line.startswith("--"):
                fpath = line.split(":")[0]
                if fpath and fpath not in seen_files:
                    seen_files[fpath] = fpath

        card_lines = [f"[{Path(p).name}](<{p}>)" for p in list(seen_files)[:args.max_results]]
        summary = out[: 8000] + ("...[截断]" if len(out) > 8000 else "")
        return ToolResult(
            content=f"找到内容匹配 '{args.pattern}' 的 {len(seen_files)} 个文件：\n\n```\n{summary}\n```",
            cards=[Card(type="mv-file-list", payload="\n".join(card_lines))],
        )
