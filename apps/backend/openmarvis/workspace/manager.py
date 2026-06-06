from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class QuotaDecision:
    """write_file/edit_file 前的配额检查结果。

    action:
      - "allow": 在阈值内，直接放行
      - "warn":  超过 warn_threshold_pct 但未爆顶，允许但提示
      - "block": 写入后将超出硬上限，拒绝
    """
    action: str
    reason: str
    used_bytes: int
    limit_bytes: int
    scope: str  # "conv" | "global"


@dataclass
class Workspace:
    conv_id: str
    root_base: Path        # 通常为 settings.workspace.root

    @property
    def root(self) -> Path:
        return self.root_base / "workspaces" / self.conv_id

    @property
    def uploads_dir(self) -> Path:
        return self.root / "uploads"

    @property
    def temp_dir(self) -> Path:
        return self.root / "temp"

    @property
    def output_dir(self) -> Path:
        return self.root / "output"

    def ensure(self) -> None:
        for d in (self.uploads_dir, self.temp_dir, self.output_dir):
            d.mkdir(parents=True, exist_ok=True)

    def contains(self, path: Path) -> bool:
        try:
            resolved = Path(path).expanduser().resolve()
            root_resolved = self.root.resolve()
            return root_resolved == resolved or root_resolved in resolved.parents
        except (OSError, RuntimeError):
            return False

    def relpath(self, path: Path) -> str:
        return str(Path(path).resolve().relative_to(self.root.resolve()))

    def disk_usage(self) -> int:
        if not self.root.exists():
            return 0
        total = 0
        for p in self.root.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
        return total

    def global_disk_usage(self) -> int:
        """整个 root_base/workspaces 下所有 conv 的总字节数（用于全局配额）。"""
        workspaces_dir = self.root_base / "workspaces"
        if not workspaces_dir.exists():
            return 0
        total = 0
        for p in workspaces_dir.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
        return total

    def check_quota(
        self,
        content_size: int,
        max_per_conv_mb: int,
        max_total_gb: int,
        warn_threshold_pct: int = 80,
    ) -> QuotaDecision:
        """检查写入 content_size 字节后是否超配额。

        优先返回最严重的 decision —— block 优先于 warn 优先于 allow，
        且单会话配额优先于全局配额（更精确）。
        """
        conv_limit = max_per_conv_mb * 1024 * 1024
        global_limit = max_total_gb * 1024 * 1024 * 1024

        conv_used = self.disk_usage()
        conv_projected = conv_used + content_size

        # 1. 单会话硬上限
        if conv_projected > conv_limit:
            return QuotaDecision(
                action="block",
                reason=(f"单会话配额 {max_per_conv_mb}MB 即将超出 "
                        f"({conv_projected / 1024 / 1024:.1f}MB > {max_per_conv_mb}MB)"),
                used_bytes=conv_used,
                limit_bytes=conv_limit,
                scope="conv",
            )

        # 2. 全局硬上限
        global_used = self.global_disk_usage()
        global_projected = global_used + content_size
        if global_projected > global_limit:
            return QuotaDecision(
                action="block",
                reason=(f"全局配额 {max_total_gb}GB 即将超出 "
                        f"({global_projected / 1024 / 1024 / 1024:.2f}GB > {max_total_gb}GB)"),
                used_bytes=global_used,
                limit_bytes=global_limit,
                scope="global",
            )

        # 3. 警告阈值 —— 单会话优先
        warn_conv = conv_limit * warn_threshold_pct // 100
        if conv_projected > warn_conv:
            pct = conv_projected * 100 // conv_limit
            return QuotaDecision(
                action="warn",
                reason=(f"单会话配额已用 {pct}% "
                        f"({conv_projected / 1024 / 1024:.1f}MB / {max_per_conv_mb}MB)"),
                used_bytes=conv_used,
                limit_bytes=conv_limit,
                scope="conv",
            )

        warn_global = global_limit * warn_threshold_pct // 100
        if global_projected > warn_global:
            pct = global_projected * 100 // global_limit
            return QuotaDecision(
                action="warn",
                reason=(f"全局配额已用 {pct}% "
                        f"({global_projected / 1024 / 1024 / 1024:.2f}GB / {max_total_gb}GB)"),
                used_bytes=global_used,
                limit_bytes=global_limit,
                scope="global",
            )

        return QuotaDecision(
            action="allow", reason="在配额内",
            used_bytes=conv_used, limit_bytes=conv_limit, scope="conv",
        )


class WorkspaceManager:
    def __init__(self, root_base: Path):
        self.root_base = Path(root_base).expanduser()

    def get_or_create(self, conv_id: str) -> Workspace:
        ws = Workspace(conv_id=conv_id, root_base=self.root_base)
        ws.ensure()
        return ws
