from __future__ import annotations

import fnmatch
import os
import shutil
import time
from pathlib import Path

from pydantic import BaseModel, Field

from ..store.audit import record_write
from .base import Card, Tool, ToolContext, ToolResult

# ---------- read_text ----------


class ReadTextArgs(BaseModel):
    file_path: str = Field(description="用于读取文件的绝对路径")
    offset: int = Field(default=0, description="起始行号（0-based）")
    limit: int = Field(default=-1, description="读取的最大行数，-1 表示默认上限")


DEFAULT_READ_LINES = 2000


class ReadTextTool(Tool):
    name = "read_text"
    description = "读取纯文本文件内容（.py / .md / .json / .yaml / .txt 等）。"
    args_model = ReadTextArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    async def execute(self, args: ReadTextArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name, args=args.model_dump())
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if decision.action == "confirm":
            return ToolResult(error=f"requires_confirm: {decision.reason}")
        p = Path(args.file_path).expanduser()
        if not p.exists():
            return ToolResult(error=f"文件不存在: {p}")
        text = p.read_text(errors="replace")
        lines = text.splitlines()
        limit = args.limit if args.limit > 0 else DEFAULT_READ_LINES
        sliced = lines[args.offset : args.offset + limit]
        return ToolResult(content="\n".join(sliced))


# ---------- write_file ----------


class WriteFileArgs(BaseModel):
    file_path: str = Field(description="要写入的文件路径（绝对路径）")
    content: str = Field(description="要写入的文本内容")


class WriteFileTool(Tool):
    name = "write_file"
    description = "将文本内容写入新文件。若已存在则自动改名避免覆盖。"
    args_model = WriteFileArgs
    risk_level = "medium"
    available_to = ("main", "file-agent")

    def __init__(self, engine=None):
        self.engine = engine

    async def execute(self, args: WriteFileArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name, args=args.model_dump())
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if decision.action == "confirm":
            return ToolResult(error=f"requires_confirm: {decision.reason}")
        p = Path(args.file_path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            stem, suffix = p.stem, p.suffix
            i = 1
            while True:
                candidate = p.with_name(f"{stem}_{i}{suffix}")
                if not candidate.exists():
                    p = candidate
                    break
                i += 1
        p.write_text(args.content, encoding="utf-8")
        if self.engine is not None:
            record_write(self.engine, conv_id=ctx.conv_id, path=str(p))
        return ToolResult(content=f"已写入: {p}")


# ---------- edit_file ----------


class EditFileArgs(BaseModel):
    file_path: str
    old_str: str
    new_str: str
    replace_all: bool = False


class EditFileTool(Tool):
    name = "edit_file"
    description = "对已有文本文件做精确字符串替换。默认要求唯一匹配。"
    args_model = EditFileArgs
    risk_level = "medium"
    available_to = ("main", "file-agent")

    def __init__(self, engine=None):
        self.engine = engine

    async def execute(self, args: EditFileArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name, args=args.model_dump())
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if decision.action == "confirm":
            return ToolResult(error=f"requires_confirm: {decision.reason}")
        p = Path(args.file_path).expanduser()
        if not p.exists():
            return ToolResult(error=f"文件不存在: {p}")
        text = p.read_text()
        if args.replace_all:
            new_text = text.replace(args.old_str, args.new_str)
            count = text.count(args.old_str)
        else:
            count = text.count(args.old_str)
            if count == 0:
                return ToolResult(error=f"未找到 old_str: {args.old_str!r}")
            if count > 1:
                return ToolResult(error=f"匹配不唯一（{count} 次），请扩大上下文或用 replace_all")
            new_text = text.replace(args.old_str, args.new_str, 1)
        p.write_text(new_text, encoding="utf-8")
        if self.engine is not None:
            record_write(self.engine, conv_id=ctx.conv_id, path=str(p))
        return ToolResult(content=f"已编辑: {p}（替换 {count} 处）")


# ---------- delete ----------


class DeleteArgs(BaseModel):
    file_paths: list[str] = Field(description="要删除的文件或目录路径列表（单次最多 50 个）")


class DeleteTool(Tool):
    name = "delete"
    description = "删除文件/文件夹（移至 .trash 回收站，7 天后硬删）。"
    args_model = DeleteArgs
    risk_level = "high"  # 但 UI 自带勾选确认 → 工具层不再 ask_user
    available_to = ("main", "file-agent")

    async def execute(self, args: DeleteArgs, ctx: ToolContext) -> ToolResult:
        if len(args.file_paths) > 50:
            return ToolResult(error="单次最多 50 个路径")
        decision = ctx.security.check(
            tool=self, tool_name=self.name, args={"file_paths": args.file_paths}
        )
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        trash_base = Path("~/.openmarvis/.trash").expanduser()
        trash_dir = trash_base / f"{ctx.conv_id}_{int(time.time())}"
        trash_dir.mkdir(parents=True, exist_ok=True)
        deleted: list[Path] = []
        for raw in args.file_paths:
            p = Path(raw).expanduser()
            if not p.exists():
                continue
            target = trash_dir / p.name
            shutil.move(str(p), str(target))
            deleted.append(p)
        body = "\n".join(f"[{p.name}](<{p}>)" for p in deleted)
        return ToolResult(
            content=f"已删除 {len(deleted)} 项",
            cards=[Card(type="mv-delete-list", payload=body)],
        )


# ---------- list_dir ----------


class ListDirArgs(BaseModel):
    path: str
    show_hidden: bool = False


class ListDirTool(Tool):
    name = "list_dir"
    description = "列出目录条目。"
    args_model = ListDirArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    async def execute(self, args: ListDirArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name, args=args.model_dump())
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        p = Path(args.path).expanduser()
        if not p.is_dir():
            return ToolResult(error=f"不是目录: {p}")
        entries = []
        for child in sorted(p.iterdir()):
            if not args.show_hidden and child.name.startswith("."):
                continue
            kind = "D" if child.is_dir() else "F"
            size = child.stat().st_size if child.is_file() else 0
            entries.append(f"{kind} {size:>10}  {child.name}")
        return ToolResult(content="\n".join(entries) or "（空目录）")


# ---------- search_files ----------


class SearchFilesArgs(BaseModel):
    root: str
    name_glob: str = "*"
    contains: str | None = None
    max_results: int = 100


class SearchFilesTool(Tool):
    name = "search_files"
    description = "按文件名 glob 和可选正文关键词搜索文件。"
    args_model = SearchFilesArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    async def execute(self, args: SearchFilesArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name, args={"path": args.root})
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        root = Path(args.root).expanduser()
        hits: list[str] = []
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if not fnmatch.fnmatch(name, args.name_glob):
                    continue
                full = Path(dirpath) / name
                if args.contains:
                    try:
                        text = full.read_text(errors="ignore")
                    except OSError:
                        continue
                    if args.contains not in text:
                        continue
                hits.append(str(full))
                if len(hits) >= args.max_results:
                    break
            if len(hits) >= args.max_results:
                break
        body = "\n".join(f"[{Path(p).name}](<{p}>)" for p in hits) or "（无匹配）"
        return ToolResult(
            content=f"找到 {len(hits)} 项\n{body}",
            cards=[Card(type="mv-file-list", payload=body)] if hits else [],
        )
