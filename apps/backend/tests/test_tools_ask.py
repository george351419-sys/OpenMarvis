import asyncio

import pytest

from openmarvis.tools.ask import AskUserTool, PendingAskRegistry
from openmarvis.tools.base import ToolContext


@pytest.fixture
def ctx(tmp_path):
    class Sink:
        def __init__(self): self.events = []
        async def emit(self, name, data): self.events.append((name, data))
    return ToolContext(conv_id="c", agent_id="main", workspace=None,
                       memory_store=None, security=None, event_sink=Sink(),
                       user_settings=None), Sink()


async def test_ask_user_emits_event_and_waits(ctx):
    c, sink = ctx
    c.event_sink = sink
    registry = PendingAskRegistry()
    tool = AskUserTool(registry=registry)
    task = asyncio.create_task(tool.execute(
        AskUserTool.args_model(title="确认？", form_type="confirm",
                               display_type="text",
                               options=[{"label":"ok"},{"label":"cancel"}]), c))
    await asyncio.sleep(0.01)
    assert sink.events and sink.events[0][0] == "ask_user"
    ask_id = sink.events[0][1]["ask_id"]
    await registry.resolve(ask_id, ["ok"])
    result = await task
    assert "ok" in result.content
