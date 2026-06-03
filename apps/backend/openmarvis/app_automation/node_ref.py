from __future__ import annotations

import re
from dataclasses import dataclass

_AX_PATH_RE = re.compile(r"^\d+(/\d+)*$")


@dataclass(frozen=True)
class NodeRef:
    bundle_id: str
    window_index: int
    ax_path: str

    @property
    def ax_path_indexes(self) -> list[int]:
        return [int(p) for p in self.ax_path.split("/")]


def encode_node_ref(ref: NodeRef) -> str:
    return f"{ref.bundle_id}|{ref.window_index}|{ref.ax_path}"


def parse_node_ref(s: str) -> NodeRef:
    parts = s.split("|")
    if len(parts) != 3:
        raise ValueError(f"node_ref must be 'bundle|win|path', got: {s!r}")
    bundle, win_s, path = parts
    if not bundle:
        raise ValueError("bundle id empty")
    try:
        win = int(win_s)
    except ValueError as e:
        raise ValueError(f"window_index not int: {win_s!r}") from e
    if not _AX_PATH_RE.match(path):
        raise ValueError(f"ax_path malformed: {path!r}")
    return NodeRef(bundle_id=bundle, window_index=win, ax_path=path)
