from unittest.mock import AsyncMock, MagicMock

import pytest

from openmarvis.browser.pool import BrowserPool
from openmarvis.browser.settings import BrowserSettings
from openmarvis.browser.tools_capture import ScreenshotTool
from openmarvis.tools.base import ToolContext
from openmarvis.workspace.manager import Workspace


class FakePage:
    def __init__(self):
        self.screenshot = AsyncMock()
        self.locator = MagicMock()

    def set_default_timeout(self, ms): pass


@pytest.fixture
def setup(tmp_path):
    pool = MagicMock(spec=BrowserPool)
    pool.settings = BrowserSettings()
    page = FakePage()
    pool.get_page = AsyncMock(return_value=page)
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    return pool, page, ws


def make_ctx(ws):
    return ToolContext(conv_id="c", agent_id="sa-1", workspace=ws,
                       memory_store=None, security=None, event_sink=None,
                       user_settings=None)


async def test_screenshot_full_page(setup):
    pool, page, ws = setup
    tool = ScreenshotTool(pool=pool)
    r = await tool.execute(ScreenshotTool.args_model(full_page=True), make_ctx(ws))
    page.screenshot.assert_called_once()
    assert any(c.type == "mv-image-gallery" for c in r.cards)
    assert ".png" in r.cards[0].payload


async def test_screenshot_selector(setup):
    pool, page, ws = setup
    page.locator.return_value.first = MagicMock(screenshot=AsyncMock())
    tool = ScreenshotTool(pool=pool)
    r = await tool.execute(ScreenshotTool.args_model(selector="header"), make_ctx(ws))
    page.locator.assert_called_with("header")
    assert r.error is None
