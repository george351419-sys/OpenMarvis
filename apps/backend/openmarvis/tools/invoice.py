"""invoice_detection / invoice_parsing — 发票识别与解析工具。

invoice_detection: 批量判断文件是否为发票（PDF/图片均支持）
invoice_parsing:   提取单张发票的结构化字段（发票号/日期/金额/税号/购销方）
两者都使用 LLM 视觉能力（analyze_image）实现，因此需要 llm 实例。
"""
from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
from pathlib import Path

from pydantic import BaseModel, Field

from .base import Card, Tool, ToolContext, ToolResult

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".tiff"}
_PDF_EXT = ".pdf"

_BRIEF_GUARD = "\n\n[输出约束] 只输出 JSON，不要任何额外说明。"


def _encode_b64(path: Path) -> tuple[str, str]:
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return mime, data


def _is_image(p: Path) -> bool:
    return p.suffix.lower() in _IMAGE_EXTS


def _is_supported(p: Path) -> bool:
    return _is_image(p) or p.suffix.lower() == _PDF_EXT


# ---------- invoice_detection ----------


class InvoiceDetectionArgs(BaseModel):
    file_paths: list[str] = Field(
        description="待检测文件路径列表（图片或 PDF，最多 20 个）"
    )


class InvoiceDetectionTool(Tool):
    name = "invoice_detection"
    description = (
        "批量检测文件列表中哪些是发票（增值税发票、电子发票、收据均可识别）。"
        "输入图片或 PDF 路径，返回每个文件的 is_invoice 判断结果。"
        "最多 20 个文件；单次并发 5 个。"
    )
    args_model = InvoiceDetectionArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    def __init__(self, llm=None):
        self.llm = llm

    async def _detect_one(self, path: Path) -> dict:
        if not path.exists():
            return {"path": str(path), "is_invoice": False, "reason": "文件不存在"}
        if not _is_supported(path):
            return {"path": str(path), "is_invoice": False, "reason": "不支持的文件类型"}
        if not _is_image(path):
            # For PDF, we can only do a best-effort heuristic (file name)
            name_lower = path.name.lower()
            likely = any(kw in name_lower for kw in ["发票", "invoice", "fapiao", "receipt"])
            return {
                "path": str(path),
                "is_invoice": likely,
                "reason": "PDF：仅基于文件名推断（建议用 invoice_parsing 精确识别）",
            }
        try:
            mime, data = _encode_b64(path)
            prompt = (
                "这张图片是发票吗？（增值税发票、电子发票、收据、收款凭证等均算发票）"
                "只回答 JSON：{\"is_invoice\": true/false, \"type\": \"发票类型或null\"}"
                + _BRIEF_GUARD
            )
            content_blocks = [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}},
                {"type": "text", "text": prompt},
            ]
            raw = await self.llm.complete_sync(
                messages=[{"role": "user", "content": content_blocks}]
            )
            # Extract JSON from response
            import re
            m = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
            parsed = json.loads(m.group()) if m else {"is_invoice": False}
            return {"path": str(path), **parsed}
        except Exception as e:
            return {"path": str(path), "is_invoice": False, "reason": f"识别失败: {e}"}

    async def execute(self, args: InvoiceDetectionArgs, ctx: ToolContext) -> ToolResult:
        if self.llm is None:
            return ToolResult(error="invoice_detection 未配置 LLM 客户端")
        if len(args.file_paths) > 20:
            return ToolResult(error="最多支持 20 个文件")

        paths = [Path(p).expanduser() for p in args.file_paths]
        sem = asyncio.Semaphore(5)

        async def _guarded(p: Path) -> dict:
            async with sem:
                return await self._detect_one(p)

        results = await asyncio.gather(*[_guarded(p) for p in paths])
        invoices = [r for r in results if r.get("is_invoice")]
        others = [r for r in results if not r.get("is_invoice")]

        lines = ["## 发票检测结果\n"]
        lines.append(f"**共 {len(results)} 个文件，其中 {len(invoices)} 个为发票**\n")
        if invoices:
            lines.append("### 确认为发票")
            for r in invoices:
                typ = r.get("type") or ""
                lines.append(f"- ✅ `{r['path']}`" + (f"（{typ}）" if typ else ""))
        if others:
            lines.append("\n### 非发票 / 无法识别")
            for r in others:
                reason = r.get("reason") or ""
                lines.append(f"- ❌ `{r['path']}`" + (f"（{reason}）" if reason else ""))

        card_lines = [f"[{Path(r['path']).name}](<{r['path']}>)" for r in invoices]
        return ToolResult(
            content="\n".join(lines),
            cards=[Card(type="mv-file-list", payload="\n".join(card_lines))] if card_lines else [],
        )


# ---------- invoice_parsing ----------


_PARSE_PROMPT = """请提取这张发票图片中的以下字段，以 JSON 格式返回：
{
  "invoice_no": "发票号码",
  "invoice_date": "开票日期 YYYY-MM-DD",
  "amount_total": "价税合计（¥格式）",
  "amount_tax": "税额",
  "seller_name": "销方名称",
  "seller_tax_id": "销方税号",
  "buyer_name": "购方名称",
  "buyer_tax_id": "购方税号",
  "items": ["商品/服务摘要（最多3条）"]
}
无法识别的字段填 null。只输出 JSON，不要任何说明。"""


class InvoiceParsingArgs(BaseModel):
    file_path: str = Field(description="发票图片或 PDF 的绝对路径")


class InvoiceParsingTool(Tool):
    name = "invoice_parsing"
    description = (
        "OCR 解析单张发票，提取：发票号、开票日期、价税合计、税额、"
        "购方/销方名称及税号、商品摘要。返回结构化 JSON + 可读摘要。"
    )
    args_model = InvoiceParsingArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    def __init__(self, llm=None):
        self.llm = llm

    async def execute(self, args: InvoiceParsingArgs, ctx: ToolContext) -> ToolResult:
        if self.llm is None:
            return ToolResult(error="invoice_parsing 未配置 LLM 客户端")

        p = Path(args.file_path).expanduser()
        if not p.exists():
            return ToolResult(error=f"文件不存在: {p}")
        if not _is_image(p):
            return ToolResult(
                error=f"invoice_parsing 目前只支持图片格式（{', '.join(_IMAGE_EXTS)}）；"
                      f"PDF 请先用 convert_file 转成图片再解析"
            )

        try:
            mime, data = _encode_b64(p)
            content_blocks = [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}},
                {"type": "text", "text": _PARSE_PROMPT},
            ]
            raw = await self.llm.complete_sync(
                messages=[{"role": "user", "content": content_blocks}]
            )
        except Exception as e:
            return ToolResult(error=f"LLM 调用失败: {e}")

        import re
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return ToolResult(content=f"解析结果（原始）：\n{raw}")

        try:
            parsed: dict = json.loads(m.group())
        except json.JSONDecodeError:
            return ToolResult(content=f"解析结果（JSON 格式异常）：\n{raw}")

        def _v(key: str) -> str:
            v = parsed.get(key)
            return str(v) if v is not None else "未识别"

        summary = (
            f"**发票号**: {_v('invoice_no')}\n"
            f"**开票日期**: {_v('invoice_date')}\n"
            f"**价税合计**: {_v('amount_total')}\n"
            f"**税额**: {_v('amount_tax')}\n"
            f"**销方**: {_v('seller_name')}（税号: {_v('seller_tax_id')}）\n"
            f"**购方**: {_v('buyer_name')}（税号: {_v('buyer_tax_id')}）\n"
        )
        items = parsed.get("items") or []
        if items:
            summary += "**商品摘要**: " + "；".join(str(i) for i in items[:3])

        return ToolResult(content=summary + f"\n\n```json\n{json.dumps(parsed, ensure_ascii=False, indent=2)}\n```")
