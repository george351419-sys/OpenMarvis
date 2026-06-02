from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..tools.base import Tool, ToolResult
from ._subprocess import osascript, run

SETTINGS_PANE_URIS = {
    "sound": "x-apple.systempreferences:com.apple.preference.sound",
    "display": "x-apple.systempreferences:com.apple.preference.displays",
    "network": "x-apple.systempreferences:com.apple.preference.network",
    "privacy": "x-apple.systempreferences:com.apple.preference.security?Privacy",
    "battery": "x-apple.systempreferences:com.apple.preference.battery",
    "general": "x-apple.systempreferences:com.apple.preference.general",
}


# ---------- volume ----------

class VolumeGetArgs(BaseModel):
    pass


class VolumeGetTool(Tool):
    name = "volume_get"
    description = "读取系统输出音量 (0-100)"
    args_model = VolumeGetArgs
    risk_level = "low"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        code, out = await osascript("output volume of (get volume settings)")
        if code != 0:
            return ToolResult(error=f"volume_get_failed: {out[:200]}")
        return ToolResult(content=out.strip())


class VolumeSetArgs(BaseModel):
    level: int = Field(description="0-100")


class VolumeSetTool(Tool):
    name = "volume_set"
    description = "设置系统输出音量 (0-100)"
    args_model = VolumeSetArgs
    risk_level = "medium"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        if not 0 <= args.level <= 100:
            return ToolResult(error="level 必须 0-100")
        code, out = await osascript(f"set volume output volume {args.level}")
        if code != 0:
            return ToolResult(error=f"volume_set_failed: {out[:200]}")
        return ToolResult(content=f"音量设为 {args.level}")


class VolumeMuteArgs(BaseModel):
    muted: bool


class VolumeMuteTool(Tool):
    name = "volume_mute"
    description = "静音 / 取消静音"
    args_model = VolumeMuteArgs
    risk_level = "medium"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        verb = "with" if args.muted else "without"
        code, out = await osascript(f"set volume {verb} output muted")
        if code != 0:
            return ToolResult(error=f"volume_mute_failed: {out[:200]}")
        return ToolResult(content=f"muted={args.muted}")


# ---------- brightness ----------

class BrightnessGetArgs(BaseModel):
    pass


class BrightnessGetTool(Tool):
    name = "brightness_get"
    description = "读取主显示器亮度 (0.0-1.0)"
    args_model = BrightnessGetArgs
    risk_level = "low"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        code, out = await osascript(
            'tell application "System Events" to '
            'return brightness of (first display whose primary is true)')
        if code != 0:
            return ToolResult(error=f"brightness_get_failed: {out[:200]}")
        return ToolResult(content=out.strip())


class BrightnessSetArgs(BaseModel):
    level: float = Field(description="0.0-1.0")


class BrightnessSetTool(Tool):
    name = "brightness_set"
    description = "设置主显示器亮度 (0.0-1.0)"
    args_model = BrightnessSetArgs
    risk_level = "medium"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        if not 0.0 <= args.level <= 1.0:
            return ToolResult(error="level 必须 0.0-1.0")
        code, out = await osascript(
            f'tell application "System Events" to '
            f'set brightness of (first display whose primary is true) to {args.level}')
        if code != 0:
            return ToolResult(error=f"brightness_set_failed: {out[:200]}")
        return ToolResult(content=f"亮度设为 {args.level}")


# ---------- settings pane ----------

class OpenSettingsPaneArgs(BaseModel):
    pane: Literal["sound", "display", "network", "privacy", "battery", "general"]


class OpenSettingsPaneTool(Tool):
    name = "open_settings_pane"
    description = "打开 macOS 系统设置的指定面板"
    args_model = OpenSettingsPaneArgs
    risk_level = "low"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args, ctx):
        uri = SETTINGS_PANE_URIS[args.pane]
        code, out = await run(["open", uri], timeout=5)
        if code != 0:
            return ToolResult(error=f"open_pane_failed: {out[:200]}")
        return ToolResult(content=f"已打开 {args.pane} 设置面板")
