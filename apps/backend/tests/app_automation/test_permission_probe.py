from __future__ import annotations

from openmarvis.app_automation.permission_probe import (
    PermissionStatus,
    probe_app_automation_permissions,
)


def test_permission_status_dataclass_fields():
    s = PermissionStatus(accessibility=True, screen_recording=False, issues=["x"])
    assert s.accessibility is True
    assert s.screen_recording is False
    assert s.issues == ["x"]


def test_probe_runs_without_raising(monkeypatch):
    # 默认 stub 全部权限失败 - 但 probe 必须不抛
    def stub_ax(): return False
    def stub_sr(): return False
    monkeypatch.setattr("openmarvis.app_automation.permission_probe._check_accessibility", stub_ax)
    monkeypatch.setattr("openmarvis.app_automation.permission_probe._check_screen_recording", stub_sr)
    status = probe_app_automation_permissions()
    assert status.accessibility is False
    assert status.screen_recording is False
    assert any("辅助功能" in i for i in status.issues)
    assert any("屏幕录制" in i for i in status.issues)
