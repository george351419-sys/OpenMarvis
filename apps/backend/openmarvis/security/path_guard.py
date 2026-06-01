from __future__ import annotations

import fnmatch
import glob
from pathlib import Path

from ..workspace.manager import Workspace
from .policy import Decision

SYSTEM_BLOCKLIST = [
    "/System", "/usr", "/bin", "/sbin", "/Library",
    "/private", "/etc", "/var",
]
USER_SENSITIVE_DIRS = [
    "~/.ssh", "~/.aws", "~/.kube", "~/.config/gh", "~/.gnupg",
]
SENSITIVE_FILENAMES = [
    ".env", ".env.*", "id_rsa*", "*.pem", "*.key",
    "credentials", "credentials.*",
]
MACOS_PROTECTED = [
    "/Applications",
    "/Library/LaunchDaemons", "/Library/LaunchAgents",
    "~/Library/LaunchAgents",
]


class PathGuard:
    def __init__(self, workspace: Workspace, extra_blocklist: list[str] | None = None):
        self.workspace = workspace
        self.extra_blocklist = extra_blocklist or []

    def _normalize(self, raw: str) -> Path:
        return Path(raw).expanduser().resolve()

    def _blocklist(self) -> list[Path]:
        items = SYSTEM_BLOCKLIST + USER_SENSITIVE_DIRS + MACOS_PROTECTED + self.extra_blocklist
        return [Path(p).expanduser().resolve() for p in items]

    def check_path(self, raw: str) -> Decision:
        if not Path(raw).is_absolute() and "~" not in raw:
            return Decision.confirm("非绝对路径，请确认意图", raw=raw)
        target = self._normalize(raw)
        # Detect path traversal: raw contains ".." and resolved target is outside workspace
        has_traversal = ".." in Path(raw).parts
        # Workspace-internal paths are trusted — check before system blocklist
        # so that workspaces under system dirs (e.g. /private/var on macOS) work.
        if self.workspace.contains(target):
            name = target.name
            for pat in SENSITIVE_FILENAMES:
                if fnmatch.fnmatch(name, pat):
                    return Decision.confirm(f"敏感文件名 {pat}，可能含密钥", target=str(target))
            return Decision.allow("workspace 内部")
        # Path is outside workspace — if it arrived via traversal, flag explicitly
        if has_traversal:
            return Decision.confirm(
                "path traversal detected: absolute path outside workspace",
                target=str(target),
            )
        for blocked in self._blocklist():
            if target == blocked or blocked in target.parents:
                return Decision.block(f"命中保护目录 {blocked}", target=str(target))
        name = target.name
        for pat in SENSITIVE_FILENAMES:
            if fnmatch.fnmatch(name, pat):
                return Decision.confirm(f"敏感文件名 {pat}，可能含密钥", target=str(target))
        return Decision.confirm("workspace 外部，请确认是否允许访问", target=str(target))

    def expand_wildcard(self, pattern: str) -> list[str]:
        return sorted(glob.glob(str(Path(pattern).expanduser())))
