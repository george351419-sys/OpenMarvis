"""convert_file: 通过 pandoc 做文档格式互转。

vs document_convert Skill：
- Skill：完整 sub-agent + prompt + 多步骤错误处理，适合复杂任务
- Tool：一次性调用，Main Agent 直调，适合"把这个 md 转 pdf"这种简单需求

支持的源 / 目标格式：md / markdown / docx / pdf / html / rst / txt
内部 shell-out 到 pandoc；找不到 pandoc 直接返错（不静默 fallback）。
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from ..store.audit import record_write
from .base import Card, Tool, ToolContext, ToolResult

_PATH_ALIASES = AliasChoices("file_path", "source_path", "src", "path", "filepath")
_LENIENT = ConfigDict(populate_by_name=True)

# pandoc 认识的扩展名 → pandoc format 名
_EXT_TO_FORMAT = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".docx": "docx",
    ".pdf": "pdf",
    ".html": "html",
    ".htm": "html",
    ".rst": "rst",
    ".txt": "plain",
    ".tex": "latex",
}

Fmt = Literal["md", "markdown", "docx", "pdf", "html", "rst", "txt", "tex"]
_TARGET_TO_EXT = {
    "md": ".md", "markdown": ".md",
    "docx": ".docx", "pdf": ".pdf",
    "html": ".html", "rst": ".rst",
    "txt": ".txt", "tex": ".tex",
}


class ConvertFileArgs(BaseModel):
    model_config = _LENIENT
    file_path: str = Field(
        validation_alias=_PATH_ALIASES,
        description="源文件绝对路径。",
    )
    target_format: Fmt = Field(description="目标格式：md / docx / pdf / html / rst / txt / tex")
    output_dir: str | None = Field(
        default=None,
        description=(
            "输出目录，默认 workspace 的 output/。"
            "工具会自动用源文件名 + 目标扩展名生成输出路径。"
        ),
    )


def _which(name: str) -> str | None:
    return shutil.which(name)


class ConvertFileTool(Tool):
    name = "convert_file"
    description = (
        "文档格式互转（md / docx / pdf / html / rst / txt / tex）。"
        "底层 shell-out 到 pandoc，**需要本机已安装 pandoc**（没装会明确告诉你装）。"
        "PDF 输出额外依赖 LaTeX（mactex-no-gui 或类似），缺时会自动建议改 docx。"
    )
    args_model = ConvertFileArgs
    risk_level = "medium"
    available_to = ("main", "file-agent")

    def __init__(self, engine=None):
        self.engine = engine

    async def execute(self, args: ConvertFileArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name,
                                      args=args.model_dump())
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if decision.action == "confirm":
            return ToolResult(error=f"requires_confirm: {decision.reason}")

        if _which("pandoc") is None:
            return ToolResult(error=(
                "pandoc 未安装。请先执行 `brew install pandoc`，PDF 输出还需"
                "`brew install --cask mactex-no-gui`。装好后重试本工具。"
            ))

        src = Path(args.file_path).expanduser()
        if not src.exists():
            return ToolResult(error=f"源文件不存在: {src}")
        src_ext = src.suffix.lower()
        if src_ext not in _EXT_TO_FORMAT:
            return ToolResult(error=(
                f"不支持的源扩展名 '{src_ext}'。支持: "
                f"{', '.join(sorted(_EXT_TO_FORMAT))}"
            ))

        target_ext = _TARGET_TO_EXT[args.target_format]
        if src_ext == target_ext:
            return ToolResult(error=(
                f"源已是目标格式（{src_ext}），无需转换"
            ))

        out_dir = (Path(args.output_dir).expanduser() if args.output_dir
                   else ctx.workspace.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{src.stem}{target_ext}"
        # 避免覆盖
        if out_path.exists():
            i = 1
            while (cand := out_dir / f"{src.stem}_{i}{target_ext}").exists():
                i += 1
            out_path = cand

        # 调 pandoc
        proc = await asyncio.create_subprocess_exec(
            "pandoc", str(src), "-o", str(out_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_text = stderr.decode("utf-8", errors="replace").strip()
            hint = ""
            if "pdflatex" in err_text.lower() or "latex" in err_text.lower():
                hint = (
                    "\n\n提示：PDF 输出需要 LaTeX。可选：(a) `brew install "
                    "--cask mactex-no-gui` 装 LaTeX；(b) 改用 docx 作为目标格式。"
                )
            return ToolResult(error=(
                f"pandoc 失败 (exit={proc.returncode}): {err_text[:500]}{hint}"
            ))

        if not out_path.exists() or out_path.stat().st_size == 0:
            return ToolResult(error=(
                f"pandoc 报告成功但输出文件为空: {out_path}"
            ))

        if self.engine is not None:
            record_write(self.engine, conv_id=ctx.conv_id, path=str(out_path))

        size_kb = out_path.stat().st_size / 1024
        card = Card(
            type="mv-product",
            payload=f"[{out_path.name}](<{out_path}>)",
        )
        return ToolResult(
            content=f"已转换: {src.name} → {out_path.name} ({size_kb:.1f} KB)",
            cards=[card],
        )
