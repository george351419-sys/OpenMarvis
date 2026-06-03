from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from openmarvis.app_automation.ax_backend import AXNode, RunningApp, WindowInfo
from openmarvis.app_automation.tools_app import (
    GetAXTreeTool,
    ListRunningAppsTool,
    ListWindowsTool,
    ReadWindowTextTool,
    ScreenshotWindowTool,
)


def _ctx(workspace=None):
    ctx = MagicMock()
    ctx.workspace = workspace or MagicMock(output_dir="/tmp")
    ctx.security = MagicMock()
    return ctx


@pytest.mark.asyncio
async def test_list_running_apps():
    backend = MagicMock()
    backend.list_running_apps.return_value = [
        RunningApp(bundle_id="com.apple.Notes", name="Notes", pid=1, active=True),
    ]
    tool = ListRunningAppsTool(ax=backend)
    res = await tool.execute(tool.args_model(), _ctx())
    assert "Notes" in res.content


@pytest.mark.asyncio
async def test_list_windows():
    backend = MagicMock()
    backend.list_windows.return_value = [
        WindowInfo(title="Untitled", index=0, focused=True, frame=(0, 0, 1, 1)),
    ]
    tool = ListWindowsTool(ax=backend)
    res = await tool.execute(tool.args_model(bundle_id="com.apple.Notes"), _ctx())
    assert "Untitled" in res.content


@pytest.mark.asyncio
async def test_get_ax_tree():
    backend = MagicMock()
    backend.get_ax_tree.return_value = AXNode(role="AXWindow", title="W",
                                                value=None, enabled=True,
                                                path="", children=[])
    tool = GetAXTreeTool(ax=backend)
    res = await tool.execute(
        tool.args_model(bundle_id="com.apple.Notes", max_depth=3), _ctx())
    assert "AXWindow" in res.content


@pytest.mark.asyncio
async def test_read_window_text():
    backend = MagicMock()
    backend.read_window_text.return_value = "hello world"
    tool = ReadWindowTextTool(ax=backend)
    res = await tool.execute(
        tool.args_model(bundle_id="com.apple.Notes"), _ctx())
    assert "hello world" in res.content


@pytest.mark.asyncio
async def test_screenshot_window_returns_image_card(tmp_path):
    backend = MagicMock()
    out_file = tmp_path / "shot.png"
    out_file.write_bytes(b"\x89PNG")
    backend.screenshot_window.return_value = out_file

    ctx = _ctx()
    ctx.workspace.output_dir = tmp_path
    tool = ScreenshotWindowTool(ax=backend)
    res = await tool.execute(
        tool.args_model(bundle_id="com.apple.Notes", window_index=0), ctx)
    assert any(c.type == "mv-image-gallery" for c in res.cards)
