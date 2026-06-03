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
from openmarvis.security.policy import Decision


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


@pytest.mark.asyncio
async def test_activate_app():
    backend = MagicMock()
    from openmarvis.app_automation.tools_app import ActivateAppTool
    tool = ActivateAppTool(ax=backend)
    res = await tool.execute(tool.args_model(bundle_id="com.apple.Notes"), _ctx())
    backend.activate_app.assert_called_once_with("com.apple.Notes")
    assert "activated" in res.content.lower()


@pytest.mark.asyncio
async def test_quit_app_risk_is_medium():
    from openmarvis.app_automation.tools_app import QuitAppTool
    assert QuitAppTool.risk_level == "medium"


@pytest.mark.asyncio
async def test_click_ax_node_calls_backend():
    backend = MagicMock()
    from openmarvis.app_automation.tools_app import ClickAXNodeTool
    tool = ClickAXNodeTool(ax=backend)
    res = await tool.execute(
        tool.args_model(node_ref="com.apple.Notes|0|0/1"), _ctx())
    assert backend.click_ax_node.called
    assert res.error is None


@pytest.mark.asyncio
async def test_type_text_blocks_credentials():
    backend = MagicMock()
    cred_guard = MagicMock()
    cred_guard.check_text.return_value = Decision.block("looks like api key")
    ctx = _ctx()
    ctx.security.credential_guard = cred_guard

    from openmarvis.app_automation.tools_app import TypeTextTool
    tool = TypeTextTool(ax=backend)
    res = await tool.execute(
        tool.args_model(node_ref="com.apple.Notes|0|0/1",
                          text="sk-ABCDE123"), ctx)
    assert res.error is not None
    assert "credential" in (res.error or "").lower()
    backend.type_text.assert_not_called()


@pytest.mark.asyncio
async def test_select_menu_walks_backend():
    backend = MagicMock()
    from openmarvis.app_automation.tools_app import SelectMenuTool
    tool = SelectMenuTool(ax=backend)
    res = await tool.execute(
        tool.args_model(bundle_id="com.apple.Notes",
                          path=["File", "New Note"]), _ctx())
    backend.select_menu.assert_called_once_with("com.apple.Notes", ["File", "New Note"])
    assert res.error is None
