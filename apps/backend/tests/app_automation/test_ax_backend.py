from __future__ import annotations

from unittest.mock import MagicMock, patch

from openmarvis.app_automation.ax_backend import (
    AXBackend,
    AXNotAvailable,
    RunningApp,
    WindowInfo,
)


def test_list_running_apps_returns_models():
    fake_ws = MagicMock()
    fake_app = MagicMock()
    fake_app.bundleIdentifier.return_value = "com.apple.Notes"
    fake_app.localizedName.return_value = "Notes"
    fake_app.processIdentifier.return_value = 123
    fake_app.isActive.return_value = True
    fake_ws.runningApplications.return_value = [fake_app]

    with patch("openmarvis.app_automation.ax_backend.NSWorkspace") as ns:
        ns.sharedWorkspace.return_value = fake_ws
        backend = AXBackend()
        apps = backend.list_running_apps()

    assert apps == [RunningApp(bundle_id="com.apple.Notes", name="Notes",
                                pid=123, active=True)]


def test_activate_app_unknown_bundle_raises():
    fake_ws = MagicMock()
    fake_ws.runningApplications.return_value = []
    with patch("openmarvis.app_automation.ax_backend.NSWorkspace") as ns:
        ns.sharedWorkspace.return_value = fake_ws
        backend = AXBackend()
        import pytest
        with pytest.raises(AXNotAvailable):
            backend.activate_app("com.example.no")


def test_list_windows_returns_empty_when_app_missing():
    fake_ws = MagicMock()
    fake_ws.runningApplications.return_value = []
    with patch("openmarvis.app_automation.ax_backend.NSWorkspace") as ns:
        ns.sharedWorkspace.return_value = fake_ws
        backend = AXBackend()
        wins = backend.list_windows("com.example.no")
    assert wins == []


def test_window_info_dataclass():
    w = WindowInfo(title="Untitled", index=0, focused=False,
                    frame=(0, 0, 800, 600))
    assert w.title == "Untitled"
    assert w.frame == (0, 0, 800, 600)


def test_get_ax_tree_truncates_at_depth():
    from openmarvis.app_automation.ax_backend import AXNode

    leaf = AXNode(role="AXButton", title="OK", value=None, enabled=True,
                   path="0/0", children=[])
    mid = AXNode(role="AXGroup", title=None, value=None, enabled=True,
                  path="0", children=[leaf])
    root = AXNode(role="AXWindow", title="Win", value=None, enabled=True,
                   path="", children=[mid])

    from openmarvis.app_automation.ax_backend import truncate_tree
    t = truncate_tree(root, max_depth=1)
    # depth=1 means root + one level of children, leaf should be dropped
    assert len(t.children) == 1
    assert t.children[0].children == []


def test_read_window_text_concats_titles_and_values():
    from openmarvis.app_automation.ax_backend import AXNode, collect_text

    root = AXNode(role="AXWindow", title="Win", value=None, enabled=True,
                   path="", children=[
        AXNode(role="AXStaticText", title=None, value="hello",
                enabled=True, path="0", children=[]),
        AXNode(role="AXButton", title="Cancel", value=None,
                enabled=True, path="1", children=[]),
    ])
    txt = collect_text(root)
    assert "hello" in txt
    assert "Cancel" in txt
