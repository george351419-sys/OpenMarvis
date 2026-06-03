from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

try:
    from AppKit import NSWorkspace
    from ApplicationServices import (
        AXUIElementPerformAction,
        AXUIElementSetAttributeValue,
    )
except Exception:                       # pragma: no cover — non-mac
    NSWorkspace = None                  # type: ignore
    AXUIElementPerformAction = None     # type: ignore
    AXUIElementSetAttributeValue = None # type: ignore


class AXNotAvailable(RuntimeError):  # noqa: N818
    """目标 app / window / node 不可用。"""


@dataclass
class RunningApp:
    bundle_id: str
    name: str
    pid: int
    active: bool


@dataclass
class WindowInfo:
    title: str
    index: int
    focused: bool
    frame: tuple[int, int, int, int]    # x, y, w, h


class AXBackend:
    """pyobjc Accessibility 包装。每个工具调用都拿新的 AX 树，不缓存跨调用。"""

    def list_running_apps(self) -> list[RunningApp]:
        if NSWorkspace is None:
            raise AXNotAvailable("NSWorkspace unavailable")
        ws = NSWorkspace.sharedWorkspace()
        out: list[RunningApp] = []
        for app in ws.runningApplications() or []:
            bid = app.bundleIdentifier()
            name = app.localizedName()
            pid = int(app.processIdentifier())
            active = bool(app.isActive())
            if bid:
                out.append(RunningApp(bundle_id=str(bid), name=str(name or bid),
                                       pid=pid, active=active))
        return out

    def _find_app(self, bundle_id: str):
        if NSWorkspace is None:
            raise AXNotAvailable("NSWorkspace unavailable")
        ws = NSWorkspace.sharedWorkspace()
        for app in ws.runningApplications() or []:
            if str(app.bundleIdentifier() or "") == bundle_id:
                return app
        return None

    def activate_app(self, bundle_id: str) -> None:
        app = self._find_app(bundle_id)
        if app is None:
            raise AXNotAvailable(f"app not running: {bundle_id}")
        # NSApplicationActivateIgnoringOtherApps = 1 << 1
        app.activateWithOptions_(1 << 1)

    def list_windows(self, bundle_id: str) -> list[WindowInfo]:
        app = self._find_app(bundle_id)
        if app is None:
            return []
        # 用 AX API 拿窗口；这里仅做最小可测骨架，详细 AX 树留 Task A5
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
            kAXWindowsAttribute,
        )
        ax_app = AXUIElementCreateApplication(int(app.processIdentifier()))
        err, value = AXUIElementCopyAttributeValue(ax_app, kAXWindowsAttribute, None)
        if err != 0 or value is None:
            return []
        wins: list[WindowInfo] = []
        for idx, w in enumerate(value):
            title = self._ax_attr(w, "AXTitle") or ""
            focused = bool(self._ax_attr(w, "AXMain") or False)
            frame = self._frame(w)
            wins.append(WindowInfo(title=str(title), index=idx,
                                    focused=focused, frame=frame))
        return wins

    def _ax_attr(self, element, name: str):
        from ApplicationServices import AXUIElementCopyAttributeValue
        err, value = AXUIElementCopyAttributeValue(element, name, None)
        if err != 0:
            return None
        return value

    def _frame(self, element) -> tuple[int, int, int, int]:
        # 默认值，详细解析交给后续 Task A5
        try:
            pos = self._ax_attr(element, "AXPosition")
            size = self._ax_attr(element, "AXSize")
            if pos is None or size is None:
                return (0, 0, 0, 0)
            return (int(pos.x), int(pos.y), int(size.width), int(size.height))
        except Exception:
            return (0, 0, 0, 0)

    def get_ax_tree(self, bundle_id: str, window_index: int = 0,
                    max_depth: int = 6) -> AXNode | None:
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
            kAXWindowsAttribute,
        )
        app = self._find_app(bundle_id)
        if app is None:
            return None
        ax_app = AXUIElementCreateApplication(int(app.processIdentifier()))
        err, value = AXUIElementCopyAttributeValue(ax_app, kAXWindowsAttribute, None)
        if err != 0 or value is None or window_index >= len(value):
            return None
        return truncate_tree(self._walk(value[window_index], path=""), max_depth)

    def read_window_text(self, bundle_id: str, window_index: int = 0) -> str:
        tree = self.get_ax_tree(bundle_id, window_index, max_depth=12)
        if tree is None:
            return ""
        return collect_text(tree)

    def _walk(self, element, *, path: str) -> AXNode:
        role = str(self._ax_attr(element, "AXRole") or "AXUnknown")
        title = self._ax_attr(element, "AXTitle")
        value = self._ax_attr(element, "AXValue")
        enabled = bool(self._ax_attr(element, "AXEnabled") or False)
        children_raw = self._ax_attr(element, "AXChildren") or []
        children: list[AXNode] = []
        for idx, c in enumerate(children_raw):
            child_path = f"{path}/{idx}" if path else str(idx)
            children.append(self._walk(c, path=child_path))
        return AXNode(role=role, title=str(title) if title else None,
                       value=str(value) if value is not None else None,
                       enabled=enabled, path=path, children=children)

    def _resolve_node(self, ref):
        """按 node_ref 解析到 AXUIElement；找不到抛 AXNotAvailable。"""
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
            kAXWindowsAttribute,
        )
        app = self._find_app(ref.bundle_id)
        if app is None:
            raise AXNotAvailable(f"app not running: {ref.bundle_id}")
        ax_app = AXUIElementCreateApplication(int(app.processIdentifier()))
        err, wins = AXUIElementCopyAttributeValue(ax_app, kAXWindowsAttribute, None)
        if err != 0 or wins is None or ref.window_index >= len(wins):
            raise AXNotAvailable(f"window {ref.window_index} not found")
        node = wins[ref.window_index]
        for idx in ref.ax_path_indexes:
            children = self._ax_attr(node, "AXChildren") or []
            if idx >= len(children):
                raise AXNotAvailable(f"ax_path index out of range: {idx}")
            node = children[idx]
        return node

    def click_ax_node(self, ref) -> None:
        node = self._resolve_node(ref)
        err = AXUIElementPerformAction(node, "AXPress")
        if err and err != 0:
            raise AXNotAvailable(f"AXPress failed: err={err}")

    def type_text(self, ref, text: str) -> None:
        node = self._resolve_node(ref)
        err = AXUIElementSetAttributeValue(node, "AXValue", text)
        if err and err != 0:
            raise AXNotAvailable(f"AXValue set failed: err={err}")

    def _find_menu_item(self, app, path: list[str]):
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
            kAXMenuBarAttribute,
        )
        ax_app = AXUIElementCreateApplication(int(app.processIdentifier()))
        err, mb = AXUIElementCopyAttributeValue(ax_app, kAXMenuBarAttribute, None)
        if err != 0 or mb is None:
            raise AXNotAvailable("menu bar not found")
        cur = mb
        for label in path:
            children = self._ax_attr(cur, "AXChildren") or []
            match = next((c for c in children
                          if str(self._ax_attr(c, "AXTitle") or "") == label), None)
            if match is None:
                raise AXNotAvailable(f"menu item not found: {label}")
            cur = match
        return cur

    def select_menu(self, bundle_id: str, path: list[str]) -> None:
        app = self._find_app(bundle_id)
        if app is None:
            raise AXNotAvailable(f"app not running: {bundle_id}")
        item = self._find_menu_item(app, path)
        err = AXUIElementPerformAction(item, "AXPress")
        if err and err != 0:
            raise AXNotAvailable(f"menu AXPress failed: err={err}")

    def _window_id_for_index(self, app, window_index: int) -> int | None:
        """通过 CGWindowList 在屏窗口中按 pid + 序号定位 CGWindowID。"""
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGNullWindowID,
            kCGWindowListOptionOnScreenOnly,
        )
        infos = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID) or []
        pid = int(app.processIdentifier())
        hits = [w for w in infos
                if int(w.get("kCGWindowOwnerPID", -1)) == pid]
        if window_index >= len(hits):
            return None
        return int(hits[window_index].get("kCGWindowNumber", -1))

    def screenshot_window(self, bundle_id: str, window_index: int, out_path):
        from pathlib import Path
        app = self._find_app(bundle_id)
        if app is None:
            raise AXNotAvailable(f"app not running: {bundle_id}")
        wid = self._window_id_for_index(app, window_index)
        if wid is None or wid < 0:
            raise AXNotAvailable("window not found in CGWindowList")
        _capture_window_to_png(wid, Path(out_path))
        return Path(out_path)


@dataclass
class AXNode:
    role: str
    title: str | None
    value: str | None
    enabled: bool
    path: str                            # "" for root, "0", "0/1" ...
    children: list[AXNode]


def truncate_tree(node: AXNode, max_depth: int) -> AXNode:
    if max_depth <= 0:
        return AXNode(role=node.role, title=node.title, value=node.value,
                       enabled=node.enabled, path=node.path, children=[])
    return AXNode(role=node.role, title=node.title, value=node.value,
                   enabled=node.enabled, path=node.path,
                   children=[truncate_tree(c, max_depth - 1) for c in node.children])


def collect_text(node: AXNode) -> str:
    out: list[str] = []
    if node.title:
        out.append(str(node.title))
    if node.value:
        out.append(str(node.value))
    for c in node.children:
        sub = collect_text(c)
        if sub:
            out.append(sub)
    return "\n".join(out)


def _capture_window_to_png(window_id: int, out_path) -> None:        # pragma: no cover (mac runtime)
    from pathlib import Path

    from Quartz import (
        CGRectNull,
        CGWindowListCreateImage,
        kCGWindowImageBoundsIgnoreFraming,
        kCGWindowListOptionIncludingWindow,
    )
    img = CGWindowListCreateImage(CGRectNull, kCGWindowListOptionIncludingWindow,
                                    int(window_id), kCGWindowImageBoundsIgnoreFraming)
    if img is None:
        raise AXNotAvailable("CGWindowListCreateImage returned None")
    _write_cgimage_png(img, Path(out_path))


def _write_cgimage_png(cgimage, out_path) -> None:                    # pragma: no cover
    from CoreFoundation import CFURLCreateWithFileSystemPath, kCFURLPOSIXPathStyle
    from Quartz import (
        CGImageDestinationAddImage,
        CGImageDestinationCreateWithURL,
        CGImageDestinationFinalize,
    )
    url = CFURLCreateWithFileSystemPath(None, str(out_path), kCFURLPOSIXPathStyle, False)
    dst = CGImageDestinationCreateWithURL(url, "public.png", 1, None)
    if dst is None:
        raise AXNotAvailable("CGImageDestinationCreateWithURL failed")
    CGImageDestinationAddImage(dst, cgimage, None)
    if not CGImageDestinationFinalize(dst):
        raise AXNotAvailable("CGImageDestinationFinalize failed")
