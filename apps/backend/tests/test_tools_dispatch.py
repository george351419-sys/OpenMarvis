import re

import pytest

from openmarvis.agents.base import AgentResult
from openmarvis.llm.event_sink import QueueEventSink
from openmarvis.memory.store import MemoryStore
from openmarvis.security.policy import SecurityGate
from openmarvis.store.db import create_engine, init_db
from openmarvis.store.sub_agents import SubAgentStore
from openmarvis.tools.base import ToolContext
from openmarvis.tools.dispatch import DispatchTaskTool, parse_task_envelope
from openmarvis.workspace.manager import Workspace


def test_parse_task_envelope_extracts_three_blocks():
    txt = (
        "<overall_goal>do X</overall_goal>"
        "<current_task>step 1\n/path/a.pdf</current_task>"
        "<attachments>/path/a.pdf\n/path/b.pdf</attachments>"
    )
    parsed = parse_task_envelope(txt)
    assert parsed.overall_goal == "do X"
    assert "step 1" in parsed.current_task
    assert parsed.attachments == ["/path/a.pdf", "/path/b.pdf"]


def test_parse_envelope_rejects_missing_blocks():
    with pytest.raises(ValueError):
        parse_task_envelope("no tags here")


class FakeSubAgent:
    def __init__(self, agent_id="sa-1"):
        self.agent_id = agent_id
        self.name = "file-agent"
        self.message_history = []

    async def run(self, *, user_message, memory_ids):
        return AgentResult(status="ok", final_content="done",
                           summary="done", full_content="done")


class FakeFactory:
    def build(self, **kwargs):
        return FakeSubAgent()


@pytest.fixture
def ctx(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    sink = QueueEventSink()
    return ToolContext(conv_id="c", agent_id="main", workspace=ws,
                       memory_store=MemoryStore(engine),
                       security=SecurityGate(workspace=ws), event_sink=sink,
                       user_settings=None), engine


async def test_dispatch_returns_agent_id(ctx):
    c, engine = ctx
    tool = DispatchTaskTool(factory=FakeFactory(), sub_store=SubAgentStore(engine))
    r = await tool.execute(DispatchTaskTool.args_model(
        agent_name="file-agent",
        task="<overall_goal>do</overall_goal><current_task>x</current_task>"
    ), c)
    assert "Agent ID:" in r.content
    assert re.search(r"sa-\w+", r.content)
