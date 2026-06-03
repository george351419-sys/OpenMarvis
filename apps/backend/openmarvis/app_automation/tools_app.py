from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from ..tools.base import Card, Tool, ToolContext, ToolResult
from .ax_backend import AXBackend, AXNode, AXNotAvailable


def _serialize_ax(node: AXNode) -> dict:
    return {
        "role": node.role,
        "title": node.title,
        "value": node.value,
        "enabled": node.enabled,
        "path": node.path,
        "children": [_serialize_ax(c) for c in node.children],
    }


class ListRunningAppsArgs(BaseModel):
    pass


class ListRunningAppsTool(Tool):
    name = "list_running_apps"
    description = "列出当前运行的所有 GUI 应用（bundle_id / name / pid / active）。"
    args_model = ListRunningAppsArgs
    risk_level = "low"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend):
        self.ax = ax

    async def execute(self, args: ListRunningAppsArgs, ctx: ToolContext) -> ToolResult:
        try:
            apps = self.ax.list_running_apps()
        except AXNotAvailable as e:
            return ToolResult(error=f"permission_denied: {e}")
        data = [{"bundle_id": a.bundle_id, "name": a.name,
                  "pid": a.pid, "active": a.active} for a in apps]
        return ToolResult(content=json.dumps(data, ensure_ascii=False))


class ListWindowsArgs(BaseModel):
    bundle_id: str


class ListWindowsTool(Tool):
    name = "list_windows"
    description = "列出某个 app 当前的所有窗口（title / index / focused / frame）。"
    args_model = ListWindowsArgs
    risk_level = "low"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend):
        self.ax = ax

    async def execute(self, args: ListWindowsArgs, ctx: ToolContext) -> ToolResult:
        try:
            wins = self.ax.list_windows(args.bundle_id)
        except AXNotAvailable as e:
            return ToolResult(error=f"permission_denied: {e}")
        data = [{"title": w.title, "index": w.index, "focused": w.focused,
                  "frame": list(w.frame)} for w in wins]
        return ToolResult(content=json.dumps(data, ensure_ascii=False))


class GetAXTreeArgs(BaseModel):
    bundle_id: str
    window_index: int = 0
    max_depth: int = Field(default=6, ge=1, le=20)


class GetAXTreeTool(Tool):
    name = "get_ax_tree"
    description = "拉取某个窗口的 AX 子树（结构化控件清单），供后续 click/type 决策。"
    args_model = GetAXTreeArgs
    risk_level = "low"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend):
        self.ax = ax

    async def execute(self, args: GetAXTreeArgs, ctx: ToolContext) -> ToolResult:
        try:
            tree = self.ax.get_ax_tree(args.bundle_id, args.window_index, args.max_depth)
        except AXNotAvailable as e:
            return ToolResult(error=f"permission_denied: {e}")
        if tree is None:
            return ToolResult(error="window_not_found")
        return ToolResult(content=json.dumps(_serialize_ax(tree), ensure_ascii=False))


class ReadWindowTextArgs(BaseModel):
    bundle_id: str
    window_index: int = 0


class ReadWindowTextTool(Tool):
    name = "read_window_text"
    description = "Dump 某个窗口的所有可见文本（titles + values 拼接）。"
    args_model = ReadWindowTextArgs
    risk_level = "low"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend):
        self.ax = ax

    async def execute(self, args: ReadWindowTextArgs, ctx: ToolContext) -> ToolResult:
        try:
            txt = self.ax.read_window_text(args.bundle_id, args.window_index)
        except AXNotAvailable as e:
            return ToolResult(error=f"permission_denied: {e}")
        return ToolResult(content=txt or "")


class ScreenshotWindowArgs(BaseModel):
    bundle_id: str
    window_index: int = 0


class ScreenshotWindowTool(Tool):
    name = "screenshot_window"
    description = "截取某个窗口为 PNG，回流为 mv-image-gallery 卡片。"
    args_model = ScreenshotWindowArgs
    risk_level = "low"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend):
        self.ax = ax

    async def execute(self, args: ScreenshotWindowArgs, ctx: ToolContext) -> ToolResult:
        out_dir = Path(ctx.workspace.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"app_shot_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
        try:
            self.ax.screenshot_window(args.bundle_id, args.window_index, out_path)
        except AXNotAvailable as e:
            return ToolResult(error=f"permission_denied: {e}")
        card = Card(type="mv-image-gallery",
                     payload=json.dumps({"images": [str(out_path)]}))
        return ToolResult(content=f"screenshot saved: {out_path}", cards=[card])
