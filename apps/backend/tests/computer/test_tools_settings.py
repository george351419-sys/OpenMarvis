from unittest.mock import AsyncMock, patch

from openmarvis.computer.tools_settings import (
    BrightnessSetTool,
    OpenSettingsPaneTool,
    VolumeGetTool,
    VolumeMuteTool,
    VolumeSetTool,
)
from openmarvis.tools.base import ToolContext


def ctx():
    return ToolContext(conv_id="c", agent_id="sa-1", workspace=None,
                       memory_store=None, security=None, event_sink=None,
                       user_settings=None)


@patch("openmarvis.computer.tools_settings.osascript", new_callable=AsyncMock)
async def test_volume_get(mock_o):
    mock_o.return_value = (0, "65")
    r = await VolumeGetTool().execute(VolumeGetTool.args_model(), ctx())
    assert "65" in r.content


@patch("openmarvis.computer.tools_settings.osascript", new_callable=AsyncMock)
async def test_volume_set(mock_o):
    mock_o.return_value = (0, "")
    r = await VolumeSetTool().execute(VolumeSetTool.args_model(level=50), ctx())
    assert "50" in r.content


async def test_volume_set_range_check():
    r = await VolumeSetTool().execute(VolumeSetTool.args_model(level=999), ctx())
    assert r.error and "level" in r.error.lower()


@patch("openmarvis.computer.tools_settings.osascript", new_callable=AsyncMock)
async def test_volume_mute(mock_o):
    mock_o.return_value = (0, "")
    r = await VolumeMuteTool().execute(VolumeMuteTool.args_model(muted=True), ctx())
    assert r.error is None


@patch("openmarvis.computer.tools_settings.osascript", new_callable=AsyncMock)
async def test_brightness_set_range(mock_o):
    r = await BrightnessSetTool().execute(BrightnessSetTool.args_model(level=2.0), ctx())
    assert r.error and "level" in r.error.lower()


@patch("openmarvis.computer.tools_settings.run", new_callable=AsyncMock)
async def test_open_settings_pane(mock_run):
    mock_run.return_value = (0, "")
    r = await OpenSettingsPaneTool().execute(
        OpenSettingsPaneTool.args_model(pane="sound"), ctx())
    assert r.error is None
