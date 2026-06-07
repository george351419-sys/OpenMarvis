"""send_file — 将本地文件准备为可发送状态。

将目标文件复制到 output/ 目录并生成可访问路径，用户可通过
AirDrop / Finder / 邮件等方式发送到移动端。
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from .base import Card, Tool, ToolContext, ToolResult


class SendFileArgs(BaseModel):
    file_path: str = Field(description="要发送的本地文件或目录的绝对路径")


class SendFileTool(Tool):
    name = "send_file"
    description = (
        "将本地文件准备为可发送状态，复制到工作区 output/ 并返回可访问路径。"
        "用户可通过 AirDrop、Finder、邮件等方式发送到移动端。"
        "适用于：用户希望将文件从电脑发到手机/平板时。"
    )
    args_model = SendFileArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    async def execute(self, args: SendFileArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name,
                                      args={"path": args.file_path})
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")

        src = Path(args.file_path).expanduser().resolve()
        if not src.exists():
            return ToolResult(error=f"文件不存在: {src}")

        output_dir = ctx.workspace.output_dir / "send"
        output_dir.mkdir(parents=True, exist_ok=True)

        if src.is_dir():
            dst_name = f"{src.name}_{uuid.uuid4().hex[:6]}.zip"
            dst = output_dir / dst_name
            try:
                shutil.make_archive(str(dst.with_suffix("")), "zip", src)
            except Exception as e:
                return ToolResult(error=f"打包目录失败: {e}")
        else:
            dst = output_dir / src.name
            # Avoid overwrite collision
            if dst.exists():
                dst = output_dir / f"{src.stem}_{uuid.uuid4().hex[:6]}{src.suffix}"
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                return ToolResult(error=f"复制文件失败: {e}")

        card = Card(
            type="mv-product",
            payload=f"[{dst.name}](<{dst}>)",
        )
        return ToolResult(
            content=(
                f"文件已准备好：`{dst}`\n\n"
                "发送方式：\n"
                "- **AirDrop**：在 Finder 中右键该文件 → 共享 → AirDrop\n"
                "- **邮件/消息**：将文件路径拖入邮件或消息 App\n"
                "- **隔空投送**：打开控制中心开启 AirDrop 接收"
            ),
            cards=[card],
        )
