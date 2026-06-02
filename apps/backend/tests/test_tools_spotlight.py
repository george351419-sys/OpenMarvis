from unittest.mock import AsyncMock, patch

import pytest

from openmarvis.security.policy import SecurityGate
from openmarvis.tools.base import ToolContext
from openmarvis.tools.spotlight import KIND_MAP, SpotlightTool
from openmarvis.workspace.manager import Workspace


@pytest.fixture
def ctx(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    return ToolContext(
        conv_id="c",
        agent_id="main",
        workspace=ws,
        memory_store=None,
        security=SecurityGate(workspace=ws),
        event_sink=None,
        user_settings=None,
    )


@patch(
    "openmarvis.tools.spotlight.asyncio.create_subprocess_exec",
    new_callable=AsyncMock,
)
async def test_spotlight_basic(mock_proc, ctx):
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(b"/tmp/a.pdf\n/tmp/b.pdf\n", b""))
    mock_proc.return_value = proc
    tool = SpotlightTool()
    r = await tool.execute(SpotlightTool.args_model(query="report"), ctx)
    assert "找到 2 项" in r.content
    assert any(c.type == "mv-file-list" for c in r.cards)


def test_kind_map_contains_pdf():
    assert "pdf" in KIND_MAP
    assert KIND_MAP["pdf"] == "kind:pdf"


@patch(
    "openmarvis.tools.spotlight.asyncio.create_subprocess_exec",
    new_callable=AsyncMock,
)
async def test_spotlight_with_kind(mock_proc, ctx):
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(b"/tmp/x.pdf\n", b""))
    mock_proc.return_value = proc
    tool = SpotlightTool()
    await tool.execute(SpotlightTool.args_model(query="report", kind="pdf"), ctx)
    call_args = mock_proc.call_args[0]
    assert "kind:pdf" in " ".join(call_args)


async def test_spotlight_blocks_onlyin_outside_workspace(ctx):
    tool = SpotlightTool()
    r = await tool.execute(SpotlightTool.args_model(query="x", onlyin="/etc"), ctx)
    assert r.error and "risk_blocked" in r.error
