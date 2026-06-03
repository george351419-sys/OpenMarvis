from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

try:
    from AppKit import NSWorkspace
except Exception:                       # pragma: no cover — non-mac
    NSWorkspace = None                  # type: ignore


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
