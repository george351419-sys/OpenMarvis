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


_BRIEF_GUARD = (
    "\n\n[输出约束] 请极简：只列要点/答案，禁止铺垫与寒暄；多图按 1./2./... 编号。"
)


class AnalyzeImageArgs(BaseModel):
    file_paths: list[str] = Field(description="图片绝对路径列表（1~10 张）")
    prompt: str = Field(
        default="",
        description=(
            "针对图片的具体问题。视觉调用代价高，必须在 prompt 里写明"
            "希望看到的精简格式（如'只输出 OCR 文字'/'三句话总结'）。"
        ),
    )


class AnalyzeImageTool(Tool):
    name = "analyze_image"
    description = (
        "图像理解/OCR 工具，**单次最多 10 张**。视觉模型代价高、容易啰嗦——"
        "调用时必须在 prompt 中明确精简格式。"
    )
    args_model = AnalyzeImageArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    def __init__(self, llm):
        self.llm = llm

    async def execute(self, args: AnalyzeImageArgs, ctx: ToolContext) -> ToolResult:
        if not (1 <= len(args.file_paths) <= 10):
            return ToolResult(error="file_paths 必须为 1~10 张")
        decision = ctx.security.check(tool=self, tool_name=self.name,
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
        user_prompt = args.prompt.strip() or "请描述这些图片的关键信息"
        content_blocks.append({"type": "text", "text": user_prompt + _BRIEF_GUARD})
        result_text = await self.llm.complete_sync(messages=[{"role": "user", "content": content_blocks}])
        return ToolResult(content=result_text)
