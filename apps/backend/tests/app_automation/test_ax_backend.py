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
