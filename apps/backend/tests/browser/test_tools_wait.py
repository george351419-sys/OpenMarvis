from unittest.mock import AsyncMock, MagicMock

import pytest

from openmarvis.browser.pool import BrowserPool
from openmarvis.browser.settings import BrowserSettings
from openmarvis.browser.tools_wait import WaitForSelectorTool
from openmarvis.tools.base import ToolContext


class FakePage:
    def __init__(self):
        self.wait_for_selector = AsyncMock()

    def set_default_timeout(self, ms): pass


@pytest.fixture
def fake_pool():
    pool = MagicMock(spec=BrowserPool)
    pool.settings = BrowserSettings()
    page = FakePage()
    pool.get_page = AsyncMock(return_value=page)
    return pool, page


async def test_wait_for_selector_calls_with_timeout(fake_pool):
    pool, page = fake_pool
    tool = WaitForSelectorTool(pool=pool)
    await tool.execute(WaitForSelectorTool.args_model(
        selector="div#ready", timeout=5000),
        ToolContext(conv_id="c", agent_id="sa-1", workspace=None,
                    memory_store=None, security=None, event_sink=None,
                    user_settings=None))
    page.wait_for_selector.assert_called_with("div#ready", timeout=5000)


async def test_wait_for_selector_returns_error_on_timeout(fake_pool):
    pool, page = fake_pool
    page.wait_for_selector.side_effect = Exception("Timeout")
    tool = WaitForSelectorTool(pool=pool)
    r = await tool.execute(WaitForSelectorTool.args_model(selector="div#x"),
                            ToolContext(conv_id="c", agent_id="sa-1", workspace=None,
                                        memory_store=None, security=None,
                                        event_sink=None, user_settings=None))
    assert r.error and "wait_for_selector_failed" in r.error
