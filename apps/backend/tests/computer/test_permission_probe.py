import subprocess
from unittest.mock import patch

from openmarvis.computer.permission_probe import probe_permissions


def test_probe_returns_list():
    issues = probe_permissions()
    assert isinstance(issues, list)


@patch("subprocess.run")
def test_probe_logs_missing_perms(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "osascript")
    issues = probe_permissions()
    assert len(issues) >= 1
