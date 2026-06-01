from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_RE_BLOCK = re.compile(r"```(mv-[\w-]+)\n(.*?)```", re.DOTALL)
_RE_LINE = re.compile(r"\[[^\]]+\]\(<([^>]+)>\)")


@dataclass
class Issue:
    kind: str   # missing / not_written / overlap
    detail: str


def parse_card_blocks(text: str, card_type: str) -> list[str]:
    paths: list[str] = []
    for m in _RE_BLOCK.finditer(text):
        if m.group(1) != card_type:
            continue
        for line in m.group(2).splitlines():
            mm = _RE_LINE.search(line)
            if mm:
                paths.append(mm.group(1))
    return paths


def validate_products(text: str, *, written_paths: set[str]) -> list[Issue]:
    declared = parse_card_blocks(text, "mv-product")
    issues: list[Issue] = []
    for p in declared:
        if not Path(p).exists():
            issues.append(Issue(kind="missing", detail=p))
        elif p not in written_paths:
            issues.append(Issue(kind="not_written", detail=p))
    for other in ("mv-file-list", "mv-image-gallery", "mv-video-card"):
        for p in parse_card_blocks(text, other):
            if p in declared:
                issues.append(Issue(kind="overlap", detail=f"{p} 同时出现在 {other} 与 mv-product"))
    return issues
