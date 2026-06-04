import asyncio
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


# ---- B7 同 conv 串行锁 ----


class SlowSubAgent:
    """记录调度顺序到共享列表，sleep 一小段，便于检测是否真串行。"""

    _events: list[str] = []

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.name = "file-agent"
        self.message_history: list[dict] = []

    async def run(self, *, user_message, memory_ids):
        SlowSubAgent._events.append(f"start:{self.agent_id}")
        await asyncio.sleep(0.05)
        SlowSubAgent._events.append(f"end:{self.agent_id}")
        return AgentResult(status="ok", final_content="done",
                           summary="done", full_content="done")


class SlowFactory:
    def __init__(self):
        self._n = 0

    def build(self, **kwargs):
        self._n += 1
        return SlowSubAgent(agent_id=f"sa-slow-{self._n}")


async def test_dispatch_serializes_within_same_conv(ctx):
    c, engine = ctx
    tool = DispatchTaskTool(factory=SlowFactory(), sub_store=SubAgentStore(engine))
    SlowSubAgent._events = []
    task = "<overall_goal>g</overall_goal><current_task>t</current_task>"
    args1 = DispatchTaskTool.args_model(agent_name="file-agent", task=task)
    args2 = DispatchTaskTool.args_model(agent_name="file-agent", task=task)
    # 并发发起两条同 conv dispatch
    await asyncio.gather(tool.execute(args1, c), tool.execute(args2, c))
    # 串行的话事件序列应该是 start A → end A → start B → end B
    # （不会出现 start A → start B → end ... 这种交叉）
    e = SlowSubAgent._events
    assert len(e) == 4
    assert e[0].startswith("start:") and e[1].startswith("end:")
    assert e[0].split(":")[1] == e[1].split(":")[1]
    assert e[2].startswith("start:") and e[3].startswith("end:")
    assert e[2].split(":")[1] == e[3].split(":")[1]


# ---- B8 attachments 路径校验 ----


def test_parse_envelope_accepts_real_upload(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    real = ws.uploads_dir / "doc.pdf"
    real.write_text("x")
    parsed = parse_task_envelope(
        f"<overall_goal>g</overall_goal><current_task>t</current_task>"
        f"<attachments>{real}</attachments>",
        workspace=ws,
    )
    assert parsed.attachments == [str(real)]


def test_parse_envelope_rejects_missing_attachment(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    fake = ws.uploads_dir / "ghost.pdf"  # 不创建
    with pytest.raises(ValueError, match="文件不存在"):
        parse_task_envelope(
            f"<overall_goal>g</overall_goal><current_task>t</current_task>"
            f"<attachments>{fake}</attachments>",
            workspace=ws,
        )


def test_parse_envelope_rejects_path_outside_uploads(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    outside = tmp_path / "system_file.txt"
    outside.write_text("x")
    with pytest.raises(ValueError, match="uploads"):
        parse_task_envelope(
            f"<overall_goal>g</overall_goal><current_task>t</current_task>"
            f"<attachments>{outside}</attachments>",
            workspace=ws,
        )


def test_parse_envelope_rejects_relative_attachment(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    with pytest.raises(ValueError, match="绝对路径"):
        parse_task_envelope(
            "<overall_goal>g</overall_goal><current_task>t</current_task>"
            "<attachments>relative/path.txt</attachments>",
            workspace=ws,
        )


def test_parse_envelope_without_workspace_skips_attachment_check():
    # 旧调用方式（不传 workspace）不应破——attachment 校验静默跳过
    parsed = parse_task_envelope(
        "<overall_goal>g</overall_goal><current_task>t</current_task>"
        "<attachments>/nonexistent/path.txt</attachments>"
    )
    assert parsed.attachments == ["/nonexistent/path.txt"]
