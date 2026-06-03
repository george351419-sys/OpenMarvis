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


def test_click_ax_node_invokes_press(monkeypatch):
    import openmarvis.app_automation.ax_backend as m

    pressed = {"called": False}
    def fake_press(element, action):
        pressed["called"] = True
        pressed["action"] = action
        return 0

    monkeypatch.setattr(m, "AXUIElementPerformAction", fake_press, raising=False)

    backend = AXBackend()
    fake_node = MagicMock()
    monkeypatch.setattr(backend, "_resolve_node", lambda ref: fake_node)
    from openmarvis.app_automation.node_ref import NodeRef
    backend.click_ax_node(NodeRef("com.apple.Notes", 0, "0/1"))
    assert pressed["called"] is True
    assert pressed["action"] == "AXPress"


def test_type_text_sets_value(monkeypatch):
    import openmarvis.app_automation.ax_backend as m
    seen: dict = {}

    def fake_set(element, name, value):
        seen["name"] = name
        seen["value"] = value
        return 0

    monkeypatch.setattr(m, "AXUIElementSetAttributeValue", fake_set, raising=False)
    backend = AXBackend()
    monkeypatch.setattr(backend, "_resolve_node", lambda ref: MagicMock())
    from openmarvis.app_automation.node_ref import NodeRef
    backend.type_text(NodeRef("com.apple.Notes", 0, "0/1"), "hello")
    assert seen["name"] == "AXValue"
    assert seen["value"] == "hello"


def test_select_menu_walks_path(monkeypatch):
    import openmarvis.app_automation.ax_backend as m
    calls: list[str] = []
    def fake_press(element, action):
        calls.append(action)
        return 0
    monkeypatch.setattr(m, "AXUIElementPerformAction", fake_press, raising=False)

    backend = AXBackend()
    monkeypatch.setattr(backend, "_find_menu_item", lambda app, path: MagicMock())
    fake_app = MagicMock()
    fake_app.processIdentifier.return_value = 123
    monkeypatch.setattr(backend, "_find_app", lambda b: fake_app)
    backend.select_menu("com.apple.Notes", ["File", "New Note"])
    assert calls == ["AXPress"]


def test_screenshot_window_writes_png(tmp_path, monkeypatch):
    backend = AXBackend()
    fake_app = MagicMock()
    fake_app.processIdentifier.return_value = 999
    monkeypatch.setattr(backend, "_find_app", lambda b: fake_app)

    # stub windows
    monkeypatch.setattr(backend, "_window_id_for_index", lambda app, idx: 42)

    captured = {}

    def fake_capture(window_id, out_path):
        # write a 1-byte placeholder so the file exists
        from pathlib import Path
        Path(out_path).write_bytes(b"\x89PNG\r\n\x1a\n")
        captured["window_id"] = window_id
        captured["path"] = out_path

    import openmarvis.app_automation.ax_backend as m
    monkeypatch.setattr(m, "_capture_window_to_png", fake_capture, raising=False)

    out = backend.screenshot_window("com.apple.Notes", 0, tmp_path / "shot.png")
    assert out.exists()
    assert captured["window_id"] == 42
