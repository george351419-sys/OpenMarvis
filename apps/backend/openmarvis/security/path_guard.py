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
    ".env", ".env.*", "id_rsa*", "*_rsa", "*.pem", "*.key",
    "credentials", "credentials.*",
]
MACOS_PROTECTED = [
    "/Applications",
    "/Library/LaunchDaemons", "/Library/LaunchAgents",
    "~/Library/LaunchAgents", "~/Library/LaunchDaemons",
    "~/Library/Containers",
    "/Volumes",
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

    def _check_sensitive_name(self, target: Path) -> Decision | None:
        """Return a confirm Decision if target filename matches a sensitive pattern, else None."""
        for pat in SENSITIVE_FILENAMES:
            if fnmatch.fnmatch(target.name, pat):
                return Decision.confirm(f"敏感文件名 {pat}，可能含密钥", target=str(target))
        return None

    def _check_outside_workspace(self, target: Path, has_traversal: bool,
                                   raw: str) -> Decision:
        """Classify a path that is confirmed to be outside the workspace root."""
        # details 三件套：原文、解析后的真实绝对路径、是否含 ../ 跳转。
        # 调用方（前端 ask_user 卡 / 安全审计）可以据此告诉用户
        # "此操作将访问 /Users/X/secret/foo（路径含 ../ 跳转）" 而不是只看到
        # confirm 一个 enum。
        ctx = {"raw_path": raw, "resolved_path": str(target),
               "has_traversal": has_traversal}
        # Paths inside root_base but outside workspace root → confirm, not block.
        # (macOS tmp_path is under /private; we don't want to block workspace siblings.)
        root_base_resolved = self.workspace.root_base.resolve()
        if root_base_resolved == target or root_base_resolved in target.parents:
            sensitive = self._check_sensitive_name(target)
            if sensitive is not None:
                return Decision.confirm(sensitive.reason, **ctx)
            return Decision.confirm("workspace 外部，请确认是否允许访问", **ctx)
        if has_traversal:
            return Decision.confirm(
                f"path traversal detected: '{raw}' 跳转后落在 workspace 外 → {target}",
                **ctx,
            )
        for blocked in self._blocklist():
            if target == blocked or blocked in target.parents:
                return Decision.block(f"命中保护目录 {blocked}", blocked=str(blocked), **ctx)
        sensitive = self._check_sensitive_name(target)
        if sensitive is not None:
            return Decision.confirm(sensitive.reason, **ctx)
        return Decision.confirm("workspace 外部，请确认是否允许访问", **ctx)

    def check_path(self, raw: str) -> Decision:
        if not Path(raw).is_absolute() and "~" not in raw:
            return Decision.confirm("非绝对路径，请确认意图", raw_path=raw)
        target = self._normalize(raw)
        # Detect path traversal: raw contains ".." and resolved target is outside workspace
        has_traversal = ".." in Path(raw).parts
        # Workspace-internal paths are trusted — check before system blocklist
        # so that workspaces under system dirs (e.g. /private/var on macOS) work.
        if self.workspace.contains(target):
            sensitive = self._check_sensitive_name(target)
            return sensitive or Decision.allow("workspace 内部")
        return self._check_outside_workspace(target, has_traversal, raw)

    def expand_wildcard(self, pattern: str) -> list[str]:
        return sorted(glob.glob(str(Path(pattern).expanduser())))
