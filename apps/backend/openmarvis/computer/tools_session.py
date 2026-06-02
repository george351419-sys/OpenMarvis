from __future__ import annotations

from pydantic import BaseModel

from ..tools.base import Tool, ToolResult
from ._subprocess import osascript


class LockScreenArgs(BaseModel):
    pass


class LockScreenTool(Tool):
    name = "lock_screen"
    description = "锁屏"
    args_model = LockScreenArgs
    risk_level = "medium"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        code, out = await osascript(
            'tell application "System Events" to keystroke "q" using '
            '{control down, command down}')
        if code != 0:
            return ToolResult(error=f"lock_screen_failed: {out[:200]}")
        return ToolResult(content="已锁屏")


class SleepSystemArgs(BaseModel):
    pass


class SleepSystemTool(Tool):
    name = "sleep_system"
    description = "进入睡眠状态"
    args_model = SleepSystemArgs
    risk_level = "high"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        code, out = await osascript('tell application "System Events" to sleep')
        if code != 0:
            return ToolResult(error=f"sleep_failed: {out[:200]}")
        return ToolResult(content="已请求睡眠")


class NotificationArgs(BaseModel):
    title: str
    body: str
    subtitle: str | None = None


class NotificationTool(Tool):
    name = "notification"
    description = "发送 macOS 通知"
    args_model = NotificationArgs
    risk_level = "low"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        sub = f' subtitle "{args.subtitle}"' if args.subtitle else ""
        script = f'display notification "{args.body}" with title "{args.title}"{sub}'
        code, out = await osascript(script)
        if code != 0:
            return ToolResult(error=f"notification_failed: {out[:200]}")
        return ToolResult(content="已发送通知")
