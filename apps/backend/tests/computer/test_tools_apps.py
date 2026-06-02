from unittest.mock import AsyncMock, patch

from openmarvis.computer.tools_apps import (
    SAFE_PID_NAMES,
    AppStatusTool,
    CloseAppTool,
    KillProcessTool,
    OpenAppTool,
)
from openmarvis.tools.base import ToolContext


def make_ctx():
    return ToolContext(conv_id="c", agent_id="sa-1", workspace=None,
                       memory_store=None, security=None, event_sink=None,
                       user_settings=None)


@patch("openmarvis.computer.tools_apps.run", new_callable=AsyncMock)
async def test_open_app(mock_run):
    mock_run.return_value = (0, "")
    tool = OpenAppTool()
    r = await tool.execute(OpenAppTool.args_model(app_name="Finder"), make_ctx())
    mock_run.assert_called_once()
    assert r.error is None


@patch("openmarvis.computer.tools_apps.osascript", new_callable=AsyncMock)
async def test_close_app_quit(mock_osascript):
    mock_osascript.return_value = (0, "")
    tool = CloseAppTool()
    await tool.execute(CloseAppTool.args_model(app_name="Notes", force=False), make_ctx())
    cmd = mock_osascript.call_args[0][0]
    assert "quit" in cmd


@patch("openmarvis.computer.tools_apps.run", new_callable=AsyncMock)
async def test_close_app_force_uses_killall(mock_run):
    mock_run.return_value = (0, "")
    tool = CloseAppTool()
    await tool.execute(CloseAppTool.args_model(app_name="Notes", force=True), make_ctx())
    cmd = mock_run.call_args[0][0]
    assert "killall" in cmd


@patch("openmarvis.computer.tools_apps.run", new_callable=AsyncMock)
async def test_app_status_running(mock_run):
    mock_run.return_value = (0, "true")
    tool = AppStatusTool()
    r = await tool.execute(AppStatusTool.args_model(app_name="Notes"), make_ctx())
    assert "running" in r.content.lower() or "true" in r.content


async def test_kill_process_blocks_low_pid():
    tool = KillProcessTool()
    r = await tool.execute(KillProcessTool.args_model(pid=42), make_ctx())
    assert r.error and "system_pid_protected" in r.error


@patch("openmarvis.computer.tools_apps.run", new_callable=AsyncMock)
async def test_kill_process_blocks_safe_name(mock_run):
    mock_run.side_effect = [
        (0, "WindowServer\n"),   # ps -p {pid} -o comm=
        (0, ""),                  # kill (should not be called)
    ]
    tool = KillProcessTool()
    r = await tool.execute(KillProcessTool.args_model(pid=600), make_ctx())
    assert r.error and "protected" in r.error.lower()


def test_safe_pid_names_non_empty():
    assert "WindowServer" in SAFE_PID_NAMES
    assert "launchd" in SAFE_PID_NAMES
