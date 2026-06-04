from pathlib import Path

from openmarvis.security.path_guard import PathGuard
from openmarvis.workspace.manager import Workspace


def make_ws(tmp_path: Path) -> Workspace:
    ws = Workspace(conv_id="conv_a", root_base=tmp_path)
    ws.ensure()
    return ws


def test_block_system_path(tmp_path):
    g = PathGuard(workspace=make_ws(tmp_path))
    d = g.check_path("/System/Library/Foo")
    assert d.action == "block"


def test_confirm_sensitive_filename(tmp_path):
    g = PathGuard(workspace=make_ws(tmp_path))
    d = g.check_path(str(Path.home() / "project" / ".env"))
    assert d.action == "confirm"


def test_allow_inside_workspace(tmp_path):
    ws = make_ws(tmp_path)
    g = PathGuard(workspace=ws)
    d = g.check_path(str(ws.output_dir / "report.md"))
    assert d.action == "allow"


def test_confirm_path_traversal_to_outside(tmp_path):
    ws = make_ws(tmp_path)
    g = PathGuard(workspace=ws)
    sneaky = ws.output_dir / ".." / ".." / "elsewhere.txt"
    d = g.check_path(str(sneaky))
    assert d.action in ("confirm", "block")
    assert (
        "absolute" in d.reason.lower()
        or "outside" in d.reason.lower()
        or "traversal" in d.reason.lower()
        or "外部" in d.reason
    )


def test_block_ssh_directory(tmp_path):
    g = PathGuard(workspace=make_ws(tmp_path))
    d = g.check_path(str(Path.home() / ".ssh" / "id_rsa"))
    assert d.action == "block"


def test_decision_details_include_resolved_path(tmp_path):
    # B4: Decision.details 必须带 raw_path + resolved_path，前端可以告诉
    # 用户 "此操作将访问 /Users/X/secret" 而不是只看到 confirm。
    ws = make_ws(tmp_path)
    g = PathGuard(workspace=ws)
    sneaky = ws.output_dir / ".." / ".." / "elsewhere.txt"
    d = g.check_path(str(sneaky))
    assert "raw_path" in d.details
    assert "resolved_path" in d.details
    assert d.details["has_traversal"] is True
    # resolved_path 是真实绝对路径
    assert Path(d.details["resolved_path"]).is_absolute()
    assert ".." not in d.details["resolved_path"]


def test_decision_details_on_blocked_path(tmp_path):
    g = PathGuard(workspace=make_ws(tmp_path))
    d = g.check_path("/System/Library/Foo/bar")
    assert d.action == "block"
    assert d.details.get("resolved_path", "").startswith("/System")
    assert "blocked" in d.details  # 哪条规则命中


def test_wildcard_expansion_returns_matches(tmp_path):
    ws = make_ws(tmp_path)
    (ws.output_dir / "a.txt").write_text("x")
    (ws.output_dir / "b.txt").write_text("y")
    g = PathGuard(workspace=ws)
    matches = g.expand_wildcard(str(ws.output_dir / "*.txt"))
    names = sorted(Path(m).name for m in matches)
    assert names == ["a.txt", "b.txt"]
