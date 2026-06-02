from __future__ import annotations

import logging
import subprocess

log = logging.getLogger(__name__)


def probe_permissions() -> list[str]:
    """Probe macOS permissions; return list of issues (each a human-readable str).

    Non-blocking: callers should log warnings and continue.
    """
    issues: list[str] = []
    try:
        subprocess.run(["osascript", "-e",
                         'tell application "System Events" to return name'],
                        check=True, capture_output=True, timeout=5)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        issues.append("System Events osascript 权限缺失 — "
                       "请到 系统设置 > 隐私与安全性 > 自动化 添加 Terminal/Python")
    try:
        subprocess.run(["pbpaste"], check=True, capture_output=True, timeout=2)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        issues.append("pbpaste 失败 — 剪贴板访问可能受限")
    for issue in issues:
        log.warning("Permission probe: %s", issue)
    return issues
