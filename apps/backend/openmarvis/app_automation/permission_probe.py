from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class PermissionStatus:
    accessibility: bool = False
    screen_recording: bool = False
    issues: list[str] = field(default_factory=list)


def _check_accessibility() -> bool:
    """检查 Accessibility（辅助功能）权限。"""
    try:
        from ApplicationServices import AXIsProcessTrusted
    except Exception as e:
        log.warning("import AXIsProcessTrusted failed: %s", e)
        return False
    try:
        return bool(AXIsProcessTrusted())
    except Exception as e:
        log.warning("AXIsProcessTrusted call failed: %s", e)
        return False


def _check_screen_recording() -> bool:
    """通过尝试截一小块屏来探测 Screen Recording 权限。"""
    try:
        from Quartz import (
            CGMainDisplayID,
            CGRectMake,
            CGWindowListCreateImage,
            kCGNullWindowID,
            kCGWindowImageDefault,
            kCGWindowListOptionOnScreenOnly,
        )
    except Exception as e:
        log.warning("import Quartz failed: %s", e)
        return False
    try:
        _ = CGMainDisplayID()
        rect = CGRectMake(0, 0, 1, 1)
        img = CGWindowListCreateImage(rect, kCGWindowListOptionOnScreenOnly,
                                       kCGNullWindowID, kCGWindowImageDefault)
        return img is not None
    except Exception as e:
        log.warning("screen recording probe failed: %s", e)
        return False


def probe_app_automation_permissions() -> PermissionStatus:
    s = PermissionStatus()
    s.accessibility = _check_accessibility()
    s.screen_recording = _check_screen_recording()
    if not s.accessibility:
        s.issues.append("辅助功能权限缺失 — 系统设置 > 隐私 > 辅助功能 添加运行 OpenMarvis 的进程")
    if not s.screen_recording:
        s.issues.append("屏幕录制权限缺失 — 系统设置 > 隐私 > 屏幕录制 添加运行 OpenMarvis 的进程")
    for issue in s.issues:
        log.warning("Permission probe: %s", issue)
    return s
