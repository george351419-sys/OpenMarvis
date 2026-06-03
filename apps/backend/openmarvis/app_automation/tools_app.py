from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from ..tools.base import Card, Tool, ToolContext, ToolResult
from .ax_backend import AXBackend, AXNode, AXNotAvailable
from .cliclick_runner import CliclickError, CliclickRunner
from .node_ref import parse_node_ref
from .vision_backend import VisionBackend, VisionLocateError


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



class ActivateAppArgs(BaseModel):
    bundle_id: str


class ActivateAppTool(Tool):
    name = "activate_app"
    description = "把目标应用拉到前台。"
    args_model = ActivateAppArgs
    risk_level = "low"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend):
        self.ax = ax

    async def execute(self, args: ActivateAppArgs, ctx: ToolContext) -> ToolResult:
        try:
            self.ax.activate_app(args.bundle_id)
        except AXNotAvailable as e:
            return ToolResult(error=f"app_not_found: {e}")
        return ToolResult(content=f"activated: {args.bundle_id}")


class QuitAppArgs(BaseModel):
    bundle_id: str


class QuitAppTool(Tool):
    name = "quit_app"
    description = "退出指定应用（可能丢失未保存数据 — medium risk）。"
    args_model = QuitAppArgs
    risk_level = "medium"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend):
        self.ax = ax

    async def execute(self, args: QuitAppArgs, ctx: ToolContext) -> ToolResult:
        try:
            # 用 select_menu 走 App > Quit ；AX 树里"应用菜单"通常是 menu bar 第一个子项
            self.ax.select_menu(args.bundle_id, [args.bundle_id, "Quit"])
        except AXNotAvailable:
            # fallback：osascript quit
            import subprocess
            try:
                subprocess.run(
                    ["osascript", "-e",
                      f'tell application id "{args.bundle_id}" to quit'],
                    check=True, timeout=5, capture_output=True)
            except Exception as e:
                return ToolResult(error=f"quit_failed: {e}")
        return ToolResult(content=f"quit: {args.bundle_id}")


class ClickAXNodeArgs(BaseModel):
    node_ref: str


class ClickAXNodeTool(Tool):
    name = "click_ax_node"
    description = "按 node_ref 点击控件（先用 get_ax_tree 拿到 ref）。"
    args_model = ClickAXNodeArgs
    risk_level = "low"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend):
        self.ax = ax

    async def execute(self, args: ClickAXNodeArgs, ctx: ToolContext) -> ToolResult:
        try:
            ref = parse_node_ref(args.node_ref)
            self.ax.click_ax_node(ref)
        except ValueError as e:
            return ToolResult(error=f"bad_node_ref: {e}")
        except AXNotAvailable as e:
            return ToolResult(error=f"click_failed: {e}")
        return ToolResult(content=f"clicked: {args.node_ref}")


class TypeTextArgs(BaseModel):
    node_ref: str
    text: str


class TypeTextTool(Tool):
    name = "type_text"
    description = "在文本框节点写入文本（自动 CredentialGuard 拦截凭据）。"
    args_model = TypeTextArgs
    risk_level = "low"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend):
        self.ax = ax

    async def execute(self, args: TypeTextArgs, ctx: ToolContext) -> ToolResult:
        guard = ctx.security.credential_guard
        decision = guard.check_text(args.text)
        if decision.action == "block":
            return ToolResult(error=f"credential_blocked: {decision.reason}")
        try:
            ref = parse_node_ref(args.node_ref)
            self.ax.type_text(ref, args.text)
        except ValueError as e:
            return ToolResult(error=f"bad_node_ref: {e}")
        except AXNotAvailable as e:
            return ToolResult(error=f"type_failed: {e}")
        return ToolResult(content="typed")


class SelectMenuArgs(BaseModel):
    bundle_id: str
    path: list[str]


class SelectMenuTool(Tool):
    name = "select_menu"
    description = "按菜单路径触发 menu item，如 ['File','New Note']。"
    args_model = SelectMenuArgs
    risk_level = "low"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend):
        self.ax = ax

    async def execute(self, args: SelectMenuArgs, ctx: ToolContext) -> ToolResult:
        try:
            self.ax.select_menu(args.bundle_id, args.path)
        except AXNotAvailable as e:
            return ToolResult(error=f"menu_failed: {e}")
        return ToolResult(content=f"menu_selected: {' > '.join(args.path)}")


class VisionClickArgs(BaseModel):
    bundle_id: str
    query: str
    window_index: int = 0


class VisionClickTool(Tool):
    name = "vision_click"
    description = "AX 找不到目标时的兜底：截屏 → LLM 定位 → cliclick 点击。"
    args_model = VisionClickArgs
    risk_level = "medium"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend, vision: VisionBackend, cliclick: CliclickRunner):
        self.ax = ax
        self.vision = vision
        self.cliclick = cliclick

    async def execute(self, args: VisionClickArgs, ctx: ToolContext) -> ToolResult:
        out_dir = Path(ctx.workspace.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        shot = out_dir / f"vc_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
        try:
            self.ax.screenshot_window(args.bundle_id, args.window_index, shot)
        except AXNotAvailable as e:
            return ToolResult(error=f"screenshot_failed: {e}")
        try:
            x, y = await self.vision.locate(args.query, shot)
        except VisionLocateError as e:
            return ToolResult(error=f"vision_locate_failed: {e}")
        try:
            await self.cliclick.click(x, y)
        except CliclickError as e:
            return ToolResult(error=f"cliclick_failed: {e}")
        return ToolResult(content=f"vision_clicked @ ({x},{y})")


class VisionTypeArgs(BaseModel):
    bundle_id: str
    query: str
    text: str
    window_index: int = 0


class VisionTypeTool(Tool):
    name = "vision_type"
    description = "AX 找不到输入框时的兜底：定位 + 点击 + 输入。CredentialGuard 拦截凭据。"
    args_model = VisionTypeArgs
    risk_level = "medium"
    available_to = ("app-agent",)

    def __init__(self, ax: AXBackend, vision: VisionBackend, cliclick: CliclickRunner):
        self.ax = ax
        self.vision = vision
        self.cliclick = cliclick

    async def execute(self, args: VisionTypeArgs, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.credential_guard.check_text(args.text)
        if decision.action == "block":
            return ToolResult(error=f"credential_blocked: {decision.reason}")
        out_dir = Path(ctx.workspace.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        shot = out_dir / f"vt_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
        try:
            self.ax.screenshot_window(args.bundle_id, args.window_index, shot)
            x, y = await self.vision.locate(args.query, shot)
            await self.cliclick.click(x, y)
            await self.cliclick.type_text(args.text)
        except (AXNotAvailable, VisionLocateError, CliclickError) as e:
            return ToolResult(error=f"vision_type_failed: {e}")
        return ToolResult(content=f"vision_typed @ ({x},{y})")
