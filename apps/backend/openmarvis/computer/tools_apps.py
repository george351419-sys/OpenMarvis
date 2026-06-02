from __future__ import annotations

from pydantic import BaseModel, Field

from ..tools.base import Tool, ToolContext, ToolResult
from ._subprocess import osascript, run

SAFE_PID_NAMES = {"WindowServer", "launchd", "coreaudiod", "loginwindow",
                   "systemstats", "kernel_task", "Finder"}


class OpenAppArgs(BaseModel):
    app_name: str


class OpenAppTool(Tool):
    name = "open_app"
    description = "open -a 启动应用"
    args_model = OpenAppArgs
    risk_level = "low"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args: OpenAppArgs, ctx: ToolContext) -> ToolResult:
        code, out = await run(["open", "-a", args.app_name], timeout=10)
        if code != 0:
            return ToolResult(error=f"open_app_failed: {out[:200]}")
        return ToolResult(content=f"已启动 {args.app_name}")


class CloseAppArgs(BaseModel):
    app_name: str
    force: bool = False


class CloseAppTool(Tool):
    name = "close_app"
    description = "osascript quit 退出应用；force=true 用 killall"
    args_model = CloseAppArgs
    risk_level = "medium"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args: CloseAppArgs, ctx: ToolContext) -> ToolResult:
        if args.force:
            code, out = await run(["killall", args.app_name], timeout=5)
        else:
            code, out = await osascript(f'tell application "{args.app_name}" to quit')
        if code != 0:
            return ToolResult(error=f"close_app_failed: {out[:200]}")
        return ToolResult(content=f"已关闭 {args.app_name}")


class AppStatusArgs(BaseModel):
    app_name: str


class AppStatusTool(Tool):
    name = "app_status"
    description = "检查应用是否在运行"
    args_model = AppStatusArgs
    risk_level = "low"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args: AppStatusArgs, ctx: ToolContext) -> ToolResult:
        code, out = await osascript(
            f'tell application "System Events" to return '
            f'(name of processes) contains "{args.app_name}"')
        if code != 0:
            return ToolResult(error=f"app_status_failed: {out[:200]}")
        running = "true" in out.lower()
        return ToolResult(content=f"{args.app_name} running={running}")


class KillProcessArgs(BaseModel):
    pid: int = Field(ge=1)


class KillProcessTool(Tool):
    name = "kill_process"
    description = "kill 指定 PID；系统关键进程拒绝"
    args_model = KillProcessArgs
    risk_level = "high"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args: KillProcessArgs, ctx: ToolContext) -> ToolResult:
        if args.pid < 200:
            return ToolResult(error=f"system_pid_protected: {args.pid}")
        code, out = await run(["ps", "-p", str(args.pid), "-o", "comm="], timeout=5)
        if code == 0 and out.strip().split("/")[-1] in SAFE_PID_NAMES:
            return ToolResult(error=f"protected: 拒绝 kill 系统关键进程 {out.strip()}")
        code, out = await run(["kill", str(args.pid)], timeout=5)
        if code != 0:
            return ToolResult(error=f"kill_failed: {out[:200]}")
        return ToolResult(content=f"已 kill PID {args.pid}")
