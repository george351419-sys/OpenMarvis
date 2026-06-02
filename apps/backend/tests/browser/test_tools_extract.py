from unittest.mock import AsyncMock, MagicMock

import pytest

from openmarvis.browser.pool import BrowserPool
from openmarvis.browser.settings import BrowserSettings
from openmarvis.browser.tools_extract import ExtractTextTool, ListElementsTool
from openmarvis.tools.base import ToolContext


class FakeLocator:
    def __init__(self, n_count=3):
        self.inner_text = AsyncMock(return_value="hello world")
        self._n = n_count

    @property
    def first(self):
        return self

    async def count(self):
        return self._n

    def nth(self, i):
        sub = FakeLocator(self._n)
        sub.inner_text = AsyncMock(return_value=f"item-{i}")
        return sub

    async def get_attribute(self, name):
        return f"attr-{name}"


class FakePage:
    def __init__(self):
        self._loc = FakeLocator()

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


async def test_extract_text(fake_pool):
    pool, _ = fake_pool
    tool = ExtractTextTool(pool=pool)
    r = await tool.execute(ExtractTextTool.args_model(selector="h1"), make_ctx())
    assert "hello world" in r.content


async def test_list_elements_text_only(fake_pool):
    pool, _ = fake_pool
    tool = ListElementsTool(pool=pool)
    r = await tool.execute(ListElementsTool.args_model(selector="li",
                                                        attrs=["text"], max=10),
                            make_ctx())
    assert "item-0" in r.content
    assert "item-1" in r.content
    assert "item-2" in r.content


async def test_list_elements_with_href(fake_pool):
    pool, _ = fake_pool
    tool = ListElementsTool(pool=pool)
    r = await tool.execute(ListElementsTool.args_model(selector="a",
                                                        attrs=["text", "href"], max=2),
                            make_ctx())
    assert "attr-href" in r.content
