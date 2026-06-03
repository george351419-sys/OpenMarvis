from __future__ import annotations

import logging
from pathlib import Path

from .manifest import SkillLoadError, SkillManifest, load_skill

log = logging.getLogger(__name__)


class SkillRegistry:
    """In-memory index of installed skills keyed by manifest.name."""

    def __init__(self) -> None:
        self._items: dict[str, SkillManifest] = {}

    def scan(self, root: Path) -> int:
        """Scan `root/*/skill.yaml`; return count successfully registered.

        Failed entries are logged and skipped — one bad skill must not poison
        startup.
        """
        root = Path(root)
        if not root.is_dir():
            return 0
        count = 0
        for child in sorted(root.iterdir()):
            if not child.is_dir() or not (child / "skill.yaml").is_file():
                continue
            try:
                manifest = load_skill(child)
            except SkillLoadError as e:
                log.warning("skip skill at %s: %s", child, e)
                continue
            self._items[manifest.name] = manifest
            count += 1
        return count

    def get(self, name: str) -> SkillManifest | None:
        return self._items.get(name)

    def list(self) -> list[SkillManifest]:
        return list(self._items.values())
