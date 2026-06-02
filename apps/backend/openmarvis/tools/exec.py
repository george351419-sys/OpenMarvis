from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from .base import Tool, ToolContext, ToolResult

DEFAULT_TIMEOUT = 120


# ---------- shell_executor ----------

class ShellExecutorArgs(BaseModel):
    command: str = Field(description="要执行的 Shell 命令字符串（macOS bash/zsh）")
    timeout: int = Field(default=DEFAULT_TIMEOUT, description="超时（秒）")


class ShellExecutorTool(Tool):
    name = "shell_executor"
    description = "执行系统 Shell 命令并返回结果。在会话 workspace 目录下执行。"
    args_model = ShellExecutorArgs
    risk_level = "medium"
    available_to = ("main", "file-agent")

    async def execute(self, args: ShellExecutorArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name, args={"command": args.command})
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if decision.action == "confirm":
            return ToolResult(error=f"requires_confirm: {decision.reason}")
        cwd = ctx.workspace.root if ctx.workspace else Path.cwd()
        try:
            proc = await asyncio.create_subprocess_shell(
                args.command,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={"OPENMARVIS_WORKSPACE": str(cwd), "PATH": "/usr/local/bin:/usr/bin:/bin"},
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=args.timeout)
            return ToolResult(
                content=(stdout or b"").decode("utf-8", errors="replace")
                       + f"\n[exit_code={proc.returncode}]"
            )
        except TimeoutError:
            return ToolResult(error=f"timeout after {args.timeout}s")


# ---------- python_executor ----------

class PythonExecutorArgs(BaseModel):
    code: str = Field(default="", description="要执行的 Python 代码字符串")
    script_path: str = Field(default="", description="要执行的 .py 脚本路径（与 code 二选一）")
    timeout: int = Field(default=DEFAULT_TIMEOUT)


class PythonExecutorTool(Tool):
    name = "python_executor"
    description = "执行 Python 代码或 .py 脚本，cwd=workspace。"
    args_model = PythonExecutorArgs
    risk_level = "medium"
    available_to = ("main", "file-agent", "search-agent")

    async def execute(self, args: PythonExecutorArgs, ctx: ToolContext) -> ToolResult:
        if not args.code and not args.script_path:
            return ToolResult(error="必须提供 code 或 script_path")
        decision = ctx.security.check(tool=self, tool_name=self.name, args={"code": args.code})
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        cwd = ctx.workspace.root if ctx.workspace else Path.cwd()
        if args.script_path:
            cmd = ["python3", args.script_path]
        else:
            cmd = ["python3", "-c", args.code]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={"OPENMARVIS_WORKSPACE": str(cwd),
                     "PATH": "/usr/local/bin:/usr/bin:/bin",
                     "PYTHONIOENCODING": "utf-8"},
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=args.timeout)
            return ToolResult(
                content=(stdout or b"").decode("utf-8", errors="replace")
                       + f"\n[exit_code={proc.returncode}]"
            )
        except TimeoutError:
            return ToolResult(error=f"timeout after {args.timeout}s")
