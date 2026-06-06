from __future__ import annotations

import fnmatch
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from ..store.audit import record_write
from .base import Card, Tool, ToolContext, ToolResult


def _check_workspace_quota(ctx: ToolContext, path: Path, content_size: int):
    """如果 path 在 workspace 内，检查写入 content_size 字节后是否超配额。返回 QuotaDecision or None。"""
    if ctx.workspace is None:
        return None
    if not ctx.workspace.contains(path):
        return None
    return ctx.workspace.check_quota(
        content_size=content_size,
        max_per_conv_mb=2048,
        max_total_gb=20,
        warn_threshold_pct=80,
    )


# ---------- read_text ----------


# 部分 LLM（如 Hunyuan-turbos）会把 file_path 写成 path / filepath。这里用
# validation_alias 让 args_model 容忍这些别名；但 model_json_schema() 仍然只
# 暴露 file_path 给 LLM，避免主动引导。populate_by_name 才能让正式名通过。
_PATH_ALIASES = AliasChoices("file_path", "path", "filepath")
_LENIENT = ConfigDict(populate_by_name=True)


class ReadTextArgs(BaseModel):
    model_config = _LENIENT
    file_path: str = Field(validation_alias=_PATH_ALIASES,
                            description="用于读取文件的绝对路径")
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
    model_config = _LENIENT
    file_path: str = Field(validation_alias=_PATH_ALIASES,
                            description="要写入的文件路径（绝对路径）")
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
        # 仅对落在 workspace 内的写入计配额——外部路径由 PathGuard 决定能否写。
        content_bytes = args.content.encode("utf-8")
        quota = _check_workspace_quota(ctx, p, len(content_bytes))
        if quota is not None and quota.action == "block":
            return ToolResult(error=f"quota_exceeded: {quota.reason}")
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
        msg = f"已写入: {p}"
        if quota is not None and quota.action == "warn":
            msg += f"\n⚠️ {quota.reason}"
        return ToolResult(content=msg)


# ---------- edit_file ----------


class EditFileArgs(BaseModel):
    model_config = _LENIENT
    file_path: str = Field(validation_alias=_PATH_ALIASES)
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

    @staticmethod
    def _detect_eol(raw: str) -> str:
        """探测原文换行风格；返回 '\\r\\n' / '\\r' / '\\n'。默认 \\n。"""
        if "\r\n" in raw:
            return "\r\n"
        if "\r" in raw and "\n" not in raw:
            return "\r"
        return "\n"

    async def execute(self, args: EditFileArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name, args=args.model_dump())
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if decision.action == "confirm":
            return ToolResult(error=f"requires_confirm: {decision.reason}")
        p = Path(args.file_path).expanduser()
        if not p.exists():
            return ToolResult(error=f"文件不存在: {p}")
        # newline="" 关闭 universal newlines；默认 open 会把 \r\n 转成 \n，
        # 那样下面的 _detect_eol 就永远看不到 CRLF。Path.read_text 在 3.11 不支
        # 持 newline 参数（3.13+ 才加），所以显式 open。
        with p.open("r", encoding="utf-8", newline="") as f:
            raw = f.read()
        # 把 CRLF/CR 都先规范成 LF 再做匹配 —— LLM 给的 old_str / new_str 几乎总是 \n。
        # 写回时按原文件的换行风格还原，避免把 Windows 文件意外改成 unix 风格。
        eol = self._detect_eol(raw)
        text = raw.replace("\r\n", "\n").replace("\r", "\n")
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
        if eol != "\n":
            new_text = new_text.replace("\n", eol)
        # 配额检查：只检查净增量（不缩减时 delta ≤ 0 直接跳过）
        delta = len(new_text.encode("utf-8")) - p.stat().st_size
        if delta > 0:
            quota = _check_workspace_quota(ctx, p, delta)
            if quota is not None and quota.action == "block":
                return ToolResult(error=f"quota_exceeded: {quota.reason}")
        with p.open("w", encoding="utf-8", newline="") as f:
            f.write(new_text)
        if self.engine is not None:
            record_write(self.engine, conv_id=ctx.conv_id, path=str(p))
        return ToolResult(content=f"已编辑: {p}（替换 {count} 处）")


# ---------- delete ----------


class DeleteArgs(BaseModel):
    file_paths: list[str] = Field(description="要删除的文件或目录路径列表（单次最多 50 个）")


class DeleteTool(Tool):
    name = "delete"
    description = (
        "删除文件/文件夹（移至回收站）。"
        "高风险工具：调用后前端自动弹出文件勾选确认卡片，用户确认后执行删除。"
    )
    args_model = DeleteArgs
    risk_level = "high"
    available_to = ("main", "file-agent")

    def __init__(self, ask_registry=None):
        # ask_registry: PendingAskRegistry | None
        # None → 降级为旧的 requires_confirm 流（定时任务等无人在线场景）
        self.ask_registry = ask_registry

    async def execute(self, args: DeleteArgs, ctx: ToolContext) -> ToolResult:
        if len(args.file_paths) > 50:
            return ToolResult(error="单次最多 50 个路径")
        decision = ctx.security.check(
            tool=self, tool_name=self.name, args={"file_paths": args.file_paths}
        )
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if decision.action == "confirm":
            if self.ask_registry is not None:
                # 原生 UI 路径：发 deletion_preview 卡片，等待前端勾选回调
                ask_id, fut = self.ask_registry.create()
                payload = json.dumps({"ask_id": ask_id, "files": args.file_paths},
                                     ensure_ascii=False)
                await ctx.event_sink.emit("card", {"type": "deletion_preview",
                                                    "payload": payload})
                choices = await fut
                if not choices or choices == ["cancel"]:
                    return ToolResult(content="用户取消了删除操作")
                # choices 为用户勾选的文件路径列表（子集或全集）
                confirmed = [p for p in choices if p in args.file_paths]
                if not confirmed:
                    return ToolResult(content="用户未勾选任何文件，操作已取消")
            else:
                # 无 UI 的场景（定时任务等）：返回 requires_confirm
                return ToolResult(
                    error=(f"requires_confirm: {decision.reason} —— "
                           "delete 是高风险，无人在线无法完成原生确认，请在交互会话中执行。"),
                    cards=[Card(type="deletion_preview",
                                payload=json.dumps({"ask_id": "",
                                                    "files": args.file_paths},
                                                   ensure_ascii=False))],
                )
        else:
            confirmed = args.file_paths
        return await self._do_delete(confirmed, ctx)

    async def _do_delete(self, file_paths: list[str], ctx: ToolContext) -> ToolResult:
        deleted: list[Path] = []
        for raw in file_paths:
            p = Path(raw).expanduser()
            if not p.exists():
                continue
            moved = self._move_to_trash(p, ctx)
            if moved:
                deleted.append(p)
        body = "\n".join(f"[{p.name}](<{p}>)" for p in deleted)
        return ToolResult(
            content=f"已删除 {len(deleted)} 项",
            cards=[Card(type="mv-delete-list", payload=body)],
        )

    @staticmethod
    def _move_to_trash(p: Path, ctx) -> bool:
        """移至 macOS 系统回收站；失败则降级到 .openmarvis/.trash。"""
        try:
            subprocess.run(
                ["osascript", "-e",
                 f'tell application "Finder" to delete POSIX file "{p.resolve()}"'],
                check=True, capture_output=True, timeout=10,
            )
            return True
        except Exception:
            pass
        # fallback: .openmarvis/.trash
        try:
            trash_dir = (Path("~/.openmarvis/.trash").expanduser()
                         / f"{ctx.conv_id}_{int(time.time())}")
            trash_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(trash_dir / p.name))
            return True
        except Exception:
            return False


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
