from unittest.mock import AsyncMock, MagicMock

import pytest

from openmarvis.browser.pool import BrowserPool
from openmarvis.browser.settings import BrowserSettings
from openmarvis.browser.tools_action import ClickTool, FillTool, SubmitFormTool
from openmarvis.tools.base import ToolContext


class FakeLocator:
    def __init__(self):
        self.click = AsyncMock()
        self.fill = AsyncMock()
        self.press = AsyncMock()
        self.scroll_into_view_if_needed = AsyncMock()
        self.evaluate = AsyncMock(return_value=None)

    @property
    def first(self):
        return self


class FakePage:
    def __init__(self):
        self._loc = FakeLocator()
        self.keyboard = MagicMock(press=AsyncMock())

    def locator(self, selector):
        return self._loc

    def set_default_timeout(self, ms): pass


@pytest.fixture
def fake_pool():
    pool = MagicMock(spec=BrowserPool)
    pool.settings = BrowserSettings()
    page = FakePage()
    pool.get_page = AsyncMock(return_value=page)
    return pool, page


def make_ctx():
    return ToolContext(conv_id="c", agent_id="sa-1", workspace=None,
                       memory_store=None, security=None, event_sink=None,
                       user_settings=None)


async def test_click(fake_pool):
    pool, page = fake_pool
    tool = ClickTool(pool=pool)
    r = await tool.execute(ClickTool.args_model(selector="button#go"), make_ctx())
    page._loc.click.assert_called_once()
    assert r.error is None


async def test_fill_value(fake_pool):
    pool, page = fake_pool
    tool = FillTool(pool=pool)
    r = await tool.execute(FillTool.args_model(selector="input#email",
                                               value="user@example.com"), make_ctx())
    page._loc.fill.assert_called_with("user@example.com")
    assert r.error is None


async def test_submit_form_falls_back_to_enter(fake_pool):
    pool, page = fake_pool
    tool = SubmitFormTool(pool=pool)
    await tool.execute(SubmitFormTool.args_model(form_selector=None), make_ctx())
    page.keyboard.press.assert_called_with("Enter")
