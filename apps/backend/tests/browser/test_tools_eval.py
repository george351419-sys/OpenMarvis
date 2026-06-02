from unittest.mock import AsyncMock, MagicMock

import pytest

from openmarvis.browser.pool import BrowserPool
from openmarvis.browser.settings import BrowserSettings
from openmarvis.browser.tools_eval import EvaluateTool
from openmarvis.tools.base import ToolContext


class FakePage:
    def __init__(self):
        self.evaluate = AsyncMock(return_value={"title": "Example"})

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


async def test_evaluate_returns_json(fake_pool):
    pool, _ = fake_pool
    tool = EvaluateTool(pool=pool)
    r = await tool.execute(EvaluateTool.args_model(script="return document.title"),
                            make_ctx())
    assert "Example" in r.content


def test_assess_risk_upgrades_for_cookie_access(fake_pool):
    pool, _ = fake_pool
    tool = EvaluateTool(pool=pool)
    ra_low = tool.assess_risk(EvaluateTool.args_model(script="return document.title"), None)
    ra_high = tool.assess_risk(EvaluateTool.args_model(script="return document.cookie"), None)
    assert ra_low.level == "medium"
    assert ra_high.level == "high"


def test_assess_risk_upgrades_for_storage_or_fetch(fake_pool):
    pool, _ = fake_pool
    tool = EvaluateTool(pool=pool)
    for risky in ("localStorage.x", "sessionStorage.y", "fetch('/api')", "new XMLHttpRequest()"):
        ra = tool.assess_risk(EvaluateTool.args_model(script=risky), None)
        assert ra.level == "high", f"expected high for: {risky}"
