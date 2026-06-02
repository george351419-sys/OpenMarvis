from __future__ import annotations

import asyncio

from pydantic import BaseModel

from ..tools.base import Tool, ToolResult
from ._subprocess import run


class ClipboardReadArgs(BaseModel):
    pass


class ClipboardReadTool(Tool):
    name = "clipboard_read"
    description = "读取剪贴板（自动对疑似凭据脱敏后回写 LLM）"
    args_model = ClipboardReadArgs
    risk_level = "medium"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        code, raw = await run(["pbpaste"], timeout=5)
        if code != 0:
            return ToolResult(error=f"pbpaste_failed: {raw[:200]}")
        redacted = _redact(raw)
        warn = "\n[已对疑似凭据脱敏；原始内容未传给模型]" if redacted != raw else ""
        return ToolResult(content=redacted + warn)


class ClipboardWriteArgs(BaseModel):
    text: str


class ClipboardWriteTool(Tool):
    name = "clipboard_write"
    description = "写入剪贴板"
    args_model = ClipboardWriteArgs
    risk_level = "medium"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        proc = await asyncio.create_subprocess_exec(
            "pbcopy", stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(
            proc.communicate(args.text.encode("utf-8")), timeout=5)
        if proc.returncode != 0:
            return ToolResult(error=f"pbcopy_failed: {err.decode('utf-8', 'replace')[:200]}")
        return ToolResult(content="已写入剪贴板")


def _redact(text: str) -> str:
    from ..security.credential_guard import redact
    return redact(text)
