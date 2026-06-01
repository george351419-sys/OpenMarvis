from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
        total = 0
        for p in self.root.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
        return total


class WorkspaceManager:
    def __init__(self, root_base: Path):
        self.root_base = Path(root_base).expanduser()

    def get_or_create(self, conv_id: str) -> Workspace:
        ws = Workspace(conv_id=conv_id, root_base=self.root_base)
        ws.ensure()
        return ws
