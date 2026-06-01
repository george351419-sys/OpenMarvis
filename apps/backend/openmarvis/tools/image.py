from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from pydantic import BaseModel, Field

from .base import Tool, ToolContext, ToolResult


def encode_image_b64(path: str) -> str:
    p = Path(path).expanduser()
    mime, _ = mimetypes.guess_type(p.name)
    mime = mime or "image/png"
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


class AnalyzeImageArgs(BaseModel):
    file_paths: list[str] = Field(description="图片绝对路径列表（1~10 张）")
    prompt: str = Field(default="", description="针对图片的问题或指令，需要求精简输出")


class AnalyzeImageTool(Tool):
    name = "analyze_image"
    description = "图像理解/OCR 工具，单次最多 10 张。务必在 prompt 中要求精简输出。"
    args_model = AnalyzeImageArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    def __init__(self, llm):
        self.llm = llm

    async def execute(self, args: AnalyzeImageArgs, ctx: ToolContext) -> ToolResult:
        if not (1 <= len(args.file_paths) <= 10):
            return ToolResult(error="file_paths 必须为 1~10 张")
        decision = ctx.security.check(tool_name=self.name,
                                      args={"file_paths": args.file_paths})
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if self.llm is None:
            return ToolResult(error="未配置 LLM 客户端")
        content_blocks: list[dict] = []
        for path in args.file_paths:
            content_blocks.append({
                "type": "image",
                "source": {"type": "base64",
                           "media_type": mimetypes.guess_type(path)[0] or "image/png",
                           "data": encode_image_b64(path).split("base64,", 1)[1]},
            })
        content_blocks.append({"type": "text", "text": args.prompt or "请精简描述这些图片。"})
        result_text = await self.llm.complete_sync(messages=[{"role": "user", "content": content_blocks}])
        return ToolResult(content=result_text)
