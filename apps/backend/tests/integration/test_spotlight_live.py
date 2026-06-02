from pathlib import Path

import pytest

from openmarvis.security.policy import SecurityGate
from openmarvis.tools.base import ToolContext
from openmarvis.tools.spotlight import SpotlightTool
from openmarvis.workspace.manager import Workspace


async def test_spotlight_finds_user_documents(tmp_path):
    home_docs = Path.home() / "Documents"
    if not home_docs.exists():
        pytest.skip("no ~/Documents")
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    ctx = ToolContext(conv_id="c", agent_id="main", workspace=ws,
                      memory_store=None, security=SecurityGate(workspace=ws),
                      event_sink=None, user_settings=None)
    tool = SpotlightTool()
    r = await tool.execute(SpotlightTool.args_model(
        query="kind:pdf", max_results=5), ctx)
    assert r.content
