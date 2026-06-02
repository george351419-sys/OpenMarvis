from openmarvis.browser.pool import BrowserPool
from openmarvis.browser.settings import BrowserSettings
from openmarvis.browser.tools_extract import ExtractTextTool
from openmarvis.browser.tools_nav import NavigateTool
from openmarvis.tools.base import ToolContext
from openmarvis.workspace.manager import Workspace


async def test_browser_live_navigate_and_extract(tmp_path):
    pool = BrowserPool(settings=BrowserSettings(headless=True),
                       profile_dir_base=tmp_path / "profile")
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    ctx = ToolContext(conv_id="c", agent_id="sa-1", workspace=ws,
                      memory_store=None, security=None, event_sink=None,
                      user_settings=None)

    await NavigateTool(pool=pool).execute(
        NavigateTool.args_model(url="https://example.com"), ctx)
    r = await ExtractTextTool(pool=pool).execute(
        ExtractTextTool.args_model(selector="h1"), ctx)
    assert "Example Domain" in r.content
    await pool.shutdown()
