"""read_file: 复杂格式文档解析为纯文本（Markdown）。

read_text 只处理纯文本文件；read_file 按扩展名分派到专用解析器，
返回 LLM 友好的 Markdown 文本，支持 offset/limit 分页。

支持格式：.pdf .docx .pptx .xlsx .xlsm .csv .md .txt .json .yaml .yml
不支持的扩展名直接拒绝，让 LLM 自己处理（比如用 analyze_image 看图）。
"""
from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Callable

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from .base import Tool, ToolContext, ToolResult

_PATH_ALIASES = AliasChoices("file_path", "path", "filepath")
_LENIENT = ConfigDict(populate_by_name=True)

# 限制：避免一次性把巨大文件全塞 LLM 上下文。LLM 必须用 offset/limit 翻页。
DEFAULT_LINE_LIMIT = 2000
MAX_LINE_LIMIT = 10000
MAX_BYTES = 50 * 1024 * 1024   # 单文件 50MB 上限，超出直接拒


class ReadFileArgs(BaseModel):
    model_config = _LENIENT
    file_path: str = Field(
        validation_alias=_PATH_ALIASES,
        description="要读取的文件绝对路径。按扩展名自动分派解析器。",
    )
    offset: int = Field(default=0, ge=0, description="起始行号 (0-based)")
    limit: int = Field(
        default=DEFAULT_LINE_LIMIT,
        description=f"最多读取行数，-1 表示默认上限 {DEFAULT_LINE_LIMIT}",
    )
    sheet_name: str | None = Field(
        default=None,
        description="Excel 文件：指定 sheet 名。不传则读第一个 sheet。",
    )
    sheet_index: int | None = Field(
        default=None,
        description="Excel 文件：指定 sheet 下标（0-based）。优先级低于 sheet_name。",
    )
    read_all_sheets: bool = Field(
        default=False,
        description="Excel 文件：读所有 sheet 并合并输出（带分隔符）。",
    )


# ---------------- 各格式解析器 ----------------


def _parse_pdf(p: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(p))
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:  # noqa: BLE001
            text = f"[第 {i + 1} 页解析失败: {e}]"
        parts.append(f"## Page {i + 1}\n\n{text.strip()}")
    return "\n\n".join(parts) if parts else "[空 PDF]"


def _parse_docx(p: Path) -> str:
    from docx import Document
    doc = Document(str(p))
    lines: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = (para.style.name or "").lower() if para.style else ""
        if "heading 1" in style:
            lines.append(f"# {text}")
        elif "heading 2" in style:
            lines.append(f"## {text}")
        elif "heading 3" in style:
            lines.append(f"### {text}")
        else:
            lines.append(text)
    # 表格也吐出（每行 | 分隔）
    for ti, table in enumerate(doc.tables):
        lines.append(f"\n### Table {ti + 1}\n")
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            lines.append("| " + " | ".join(cells) + " |")
    return "\n\n".join(lines) if lines else "[空 DOCX]"


def _parse_pptx(p: Path) -> str:
    from pptx import Presentation  # type: ignore[import-untyped]
    prs = Presentation(str(p))
    parts: list[str] = []
    for si, slide in enumerate(prs.slides, start=1):
        slide_parts = [f"## Slide {si}"]
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                text = "".join(run.text for run in para.runs).strip()
                if text:
                    slide_parts.append(text)
        parts.append("\n\n".join(slide_parts))
    return "\n\n---\n\n".join(parts) if parts else "[空 PPTX]"


def _parse_xlsx_sheet(ws, sheet_name: str) -> str:
    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        rows.append(["" if v is None else str(v) for v in row])
    if not rows:
        return f"## Sheet: {sheet_name}\n\n[空]"
    # 用 Markdown 表格输出
    out = [f"## Sheet: {sheet_name}\n"]
    out.append("| " + " | ".join(rows[0]) + " |")
    out.append("| " + " | ".join("---" for _ in rows[0]) + " |")
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def _parse_xlsx(p: Path, *, sheet_name: str | None, sheet_index: int | None,
                  read_all: bool) -> str:
    from openpyxl import load_workbook
    wb = load_workbook(str(p), read_only=True, data_only=True)
    sheet_names = wb.sheetnames
    if read_all:
        return "\n\n---\n\n".join(
            _parse_xlsx_sheet(wb[name], name) for name in sheet_names
        )
    target: str
    if sheet_name and sheet_name in sheet_names:
        target = sheet_name
    elif sheet_index is not None and 0 <= sheet_index < len(sheet_names):
        target = sheet_names[sheet_index]
    else:
        target = sheet_names[0]
    return _parse_xlsx_sheet(wb[target], target)


def _parse_csv(p: Path) -> str:
    """CSV 转 Markdown 表格。"""
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    if not rows:
        return "[空 CSV]"
    buf = StringIO()
    buf.write("| " + " | ".join(rows[0]) + " |\n")
    buf.write("| " + " | ".join("---" for _ in rows[0]) + " |\n")
    for r in rows[1:]:
        buf.write("| " + " | ".join(r) + " |\n")
    return buf.getvalue().rstrip()


def _parse_plain(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _parse_json(p: Path) -> str:
    """JSON 文件：解析后用 indent=2 重新输出，便于阅读。失败时退回原文。"""
    raw = p.read_text(encoding="utf-8", errors="replace")
    try:
        parsed = json.loads(raw)
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return raw


# 扩展名 → 解析器
_PARSERS: dict[str, Callable[..., str]] = {
    ".pdf": lambda p, _a: _parse_pdf(p),
    ".docx": lambda p, _a: _parse_docx(p),
    ".pptx": lambda p, _a: _parse_pptx(p),
    ".xlsx": lambda p, a: _parse_xlsx(
        p, sheet_name=a.sheet_name, sheet_index=a.sheet_index,
        read_all=a.read_all_sheets,
    ),
    ".xlsm": lambda p, a: _parse_xlsx(
        p, sheet_name=a.sheet_name, sheet_index=a.sheet_index,
        read_all=a.read_all_sheets,
    ),
    ".csv": lambda p, _a: _parse_csv(p),
    ".md": lambda p, _a: _parse_plain(p),
    ".markdown": lambda p, _a: _parse_plain(p),
    ".txt": lambda p, _a: _parse_plain(p),
    ".log": lambda p, _a: _parse_plain(p),
    ".json": lambda p, _a: _parse_json(p),
    ".yaml": lambda p, _a: _parse_plain(p),
    ".yml": lambda p, _a: _parse_plain(p),
}


def _apply_pagination(text: str, args: ReadFileArgs) -> tuple[str, int]:
    """按行号切片。返回 (切片后的文本, 总行数)。"""
    lines = text.splitlines()
    total = len(lines)
    limit = args.limit if args.limit > 0 else DEFAULT_LINE_LIMIT
    limit = min(limit, MAX_LINE_LIMIT)
    sliced = lines[args.offset : args.offset + limit]
    return "\n".join(sliced), total


class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "读取复杂格式文档（PDF / DOCX / PPTX / XLSX / CSV / MD / TXT / JSON / YAML），"
        "返回 LLM 友好的 Markdown 文本。支持 offset/limit 分页避免一次塞爆上下文；"
        "Excel 可通过 sheet_name / sheet_index / read_all_sheets 选择。"
        "纯文本类（.md/.txt/.json）用 read_text 也可，但本工具会对 JSON 美化。"
    )
    args_model = ReadFileArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    async def execute(self, args: ReadFileArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name,
                                      args=args.model_dump())
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if decision.action == "confirm":
            return ToolResult(error=f"requires_confirm: {decision.reason}")
        p = Path(args.file_path).expanduser()
        if not p.exists():
            return ToolResult(error=f"文件不存在: {p}")
        if not p.is_file():
            return ToolResult(error=f"不是文件（可能是目录）: {p}")
        size = p.stat().st_size
        if size > MAX_BYTES:
            mb = size / 1024 / 1024
            return ToolResult(error=(
                f"文件过大: {mb:.1f}MB > 50MB 上限。请先用 shell_executor "
                "切片或派 file-agent 处理。"
            ))
        ext = p.suffix.lower()
        parser = _PARSERS.get(ext)
        if parser is None:
            return ToolResult(error=(
                f"不支持的扩展名 '{ext}'。支持: {', '.join(sorted(_PARSERS))}。"
                f"图片请用 analyze_image，其他二进制请考虑 convert_file。"
            ))
        try:
            raw = parser(p, args)
        except Exception as e:  # noqa: BLE001
            return ToolResult(error=f"解析 {ext} 失败: {e}")
        sliced, total = _apply_pagination(raw, args)
        suffix = ""
        if total > args.offset + (args.limit if args.limit > 0 else DEFAULT_LINE_LIMIT):
            suffix = (
                f"\n\n... [已截断，文件共 {total} 行；"
                f"用 offset={args.offset + len(sliced.splitlines())} 继续]"
            )
        return ToolResult(content=sliced + suffix)
