from unittest.mock import AsyncMock, MagicMock

import pytest

from openmarvis.browser.pool import BrowserPool
from openmarvis.browser.settings import BrowserSettings
from openmarvis.browser.tools_nav import (
    CurrentUrlTool,
    GoBackTool,
    NavigateTool,
)
from openmarvis.tools.base import ToolContext


class FakePage:
    def __init__(self):
        self.goto = AsyncMock()
        self.go_back = AsyncMock()
        self.url = "https://example.com/"

    def set_default_timeout(self, ms): pass


@pytest.fixture
def fake_pool(monkeypatch):
    pool = MagicMock(spec=BrowserPool)
    pool.settings = BrowserSettings(allowed_domains=[])
    page = FakePage()
    pool.get_page = AsyncMock(return_value=page)
    return pool, page


def make_ctx():
    return ToolContext(conv_id="c", agent_id="sa-1", workspace=None,
                       memory_store=None, security=None, event_sink=None,
                       user_settings=None)


async def test_navigate_calls_goto(fake_pool):
    pool, page = fake_pool
    tool = NavigateTool(pool=pool)
    r = await tool.execute(NavigateTool.args_model(url="https://example.com"), make_ctx())
    page.goto.assert_called_once()
    assert "已导航" in r.content


async def test_navigate_blocks_domain_outside_allowlist(fake_pool):
    pool, page = fake_pool
    pool.settings = BrowserSettings(allowed_domains=["example.com"])
    tool = NavigateTool(pool=pool)
    r = await tool.execute(NavigateTool.args_model(url="https://evil.test/"), make_ctx())
    assert r.error and "domain_blocked" in r.error
    page.goto.assert_not_called()


async def test_navigate_subdomain_allowed(fake_pool):
    pool, page = fake_pool
    pool.settings = BrowserSettings(allowed_domains=["example.com"])
    tool = NavigateTool(pool=pool)
    r = await tool.execute(NavigateTool.args_model(url="https://api.example.com/"), make_ctx())
    assert r.error is None


async def test_current_url(fake_pool):
    pool, page = fake_pool
    tool = CurrentUrlTool(pool=pool)
    r = await tool.execute(CurrentUrlTool.args_model(), make_ctx())
    assert "example.com" in r.content


async def test_go_back(fake_pool):
    pool, page = fake_pool
    tool = GoBackTool(pool=pool)
    await tool.execute(GoBackTool.args_model(), make_ctx())
    page.go_back.assert_called_once()
