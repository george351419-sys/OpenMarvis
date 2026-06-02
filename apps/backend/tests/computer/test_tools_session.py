from unittest.mock import AsyncMock, patch

from openmarvis.computer.tools_session import (
    LockScreenTool,
    NotificationTool,
    SleepSystemTool,
)
from openmarvis.tools.base import ToolContext


def ctx():
    return ToolContext(conv_id="c", agent_id="sa-1", workspace=None,
                       memory_store=None, security=None, event_sink=None,
                       user_settings=None)


@patch("openmarvis.computer.tools_session.osascript", new_callable=AsyncMock)
async def test_lock_screen(mock_o):
    mock_o.return_value = (0, "")
    r = await LockScreenTool().execute(LockScreenTool.args_model(), ctx())
    assert r.error is None


@patch("openmarvis.computer.tools_session.osascript", new_callable=AsyncMock)
async def test_sleep_system(mock_o):
    mock_o.return_value = (0, "")
    r = await SleepSystemTool().execute(SleepSystemTool.args_model(), ctx())
    assert r.error is None


@patch("openmarvis.computer.tools_session.osascript", new_callable=AsyncMock)
async def test_notification(mock_o):
    mock_o.return_value = (0, "")
    r = await NotificationTool().execute(
        NotificationTool.args_model(title="t", body="b"), ctx())
    assert r.error is None
    mock_o.assert_called_once()
