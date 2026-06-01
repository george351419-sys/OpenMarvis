import httpx
import pytest
import respx

from openmarvis.security.policy import SecurityGate
from openmarvis.tools.base import ToolContext
from openmarvis.tools.web import WebFetchTool, WebSearchTool
from openmarvis.workspace.manager import Workspace


@pytest.fixture
def ctx(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    class Sink:
        async def emit(self, *a, **k): pass
    return ToolContext(conv_id="c", agent_id="main", workspace=ws,
                       memory_store=None, security=SecurityGate(workspace=ws),
                       event_sink=Sink(), user_settings=None)


@respx.mock
async def test_web_search_returns_results(ctx):
    respx.post("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=httpx.Response(
            200,
            json={"web": {"results": [
                {"title": "T1", "url": "https://a.example/1", "description": "D1"},
                {"title": "T2", "url": "https://a.example/2", "description": "D2"},
            ]}},
        )
    )
    tool = WebSearchTool(api_key="fake")
    r = await tool.execute(WebSearchTool.args_model(query="hello"), ctx)
    assert "T1" in r.content and "T2" in r.content


@respx.mock
async def test_web_fetch_returns_markdown(ctx):
    respx.get("https://example.com/blog").mock(
        return_value=httpx.Response(
            200, text="<html><body><h1>Hi</h1><p>Body</p></body></html>",
            headers={"content-type": "text/html"},
        )
    )
    tool = WebFetchTool()
    r = await tool.execute(WebFetchTool.args_model(url="https://example.com/blog"), ctx)
    assert "Hi" in r.content
