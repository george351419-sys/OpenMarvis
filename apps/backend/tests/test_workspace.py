from pathlib import Path

import pytest

from openmarvis.workspace.manager import Workspace, WorkspaceManager


def test_workspace_creates_subdirs(tmp_path):
    ws = Workspace(conv_id="conv_abc", root_base=tmp_path)
    ws.ensure()
    assert (tmp_path / "workspaces" / "conv_abc" / "uploads").is_dir()
    assert (tmp_path / "workspaces" / "conv_abc" / "temp").is_dir()
    assert (tmp_path / "workspaces" / "conv_abc" / "output").is_dir()


def test_workspace_contains_returns_true_for_inside(tmp_path):
    ws = Workspace(conv_id="conv_abc", root_base=tmp_path)
    ws.ensure()
    inside = ws.output_dir / "x.txt"
    inside.write_text("hi")
    assert ws.contains(inside) is True


def test_workspace_contains_returns_false_for_outside(tmp_path):
    ws = Workspace(conv_id="conv_abc", root_base=tmp_path)
    ws.ensure()
    outside = tmp_path / "elsewhere.txt"
    outside.write_text("nope")
    assert ws.contains(outside) is False


def test_workspace_contains_rejects_path_traversal(tmp_path):
    ws = Workspace(conv_id="conv_abc", root_base=tmp_path)
    ws.ensure()
    sneaky = ws.output_dir / ".." / ".." / ".." / "etc" / "passwd"
    assert ws.contains(sneaky) is False


def test_manager_get_or_create_idempotent(tmp_path):
    mgr = WorkspaceManager(root_base=tmp_path)
    a = mgr.get_or_create("conv_1")
    b = mgr.get_or_create("conv_1")
    assert a.root == b.root
