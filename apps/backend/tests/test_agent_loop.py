import pytest
from pydantic import BaseModel

from openmarvis.agents.base import AgentBase, AgentResult
from openmarvis.llm.client import StreamChunk
from openmarvis.llm.event_sink import QueueEventSink
from openmarvis.security.policy import SecurityGate
from openmarvis.tools.base import Tool, ToolContext, ToolResult
from openmarvis.tools.registry import ToolRegistry
from openmarvis.workspace.manager import Workspace


class DummyArgs(BaseModel):
    n: int


class DummyTool(Tool):
    name = "double"
    description = "返回 n*2"
    args_model = DummyArgs
    risk_level = "low"
    available_to = ("agent",)

    async def execute(self, args: DummyArgs, ctx: ToolContext) -> ToolResult:
        return ToolResult(content=str(args.n * 2))


class ScriptedLLM:
    def __init__(self, script):
        self.script = list(script)

    async def stream_chat(self, *, messages, tools):
        for chunk in self.script.pop(0):
            yield chunk


@pytest.fixture
def ws(tmp_path):
    w = Workspace(conv_id="c", root_base=tmp_path)
    w.ensure()
    return w


async def test_loop_handles_tool_use_then_end_turn(ws):
    sink = QueueEventSink()
    reg = ToolRegistry()
    reg.register(DummyTool())
    llm = ScriptedLLM([
        [StreamChunk(tool_calls=[{"id": "tc1", "name": "double", "args": {"n": 3}}], stop_reason="tool_use")],
        [StreamChunk(text="answer is 6"), StreamChunk(stop_reason="end_turn")],
    ])
    agent = AgentBase(
        name="agent", agent_id="a-1", conv_id="c",
        system_prompt="hello", llm=llm, tool_registry=reg,
        workspace=ws, memory_store=None,
        security=SecurityGate(workspace=ws), event_sink=sink,
        user_settings=None,
    )
    result = await agent.run(user_message="please double 3", memory_ids=[])
    assert isinstance(result, AgentResult)
    assert "answer is 6" in result.final_content


class FakeExecutorArgs(BaseModel):
    code: str = ""


class FakePythonExecutor(Tool):
    name = "python_executor"
    description = "fake"
    args_model = FakeExecutorArgs
    risk_level = "medium"
    available_to = ("main", "agent")

    async def execute(self, args, ctx):
        return ToolResult(content="ok")


async def _collect_warnings(sink: QueueEventSink) -> list[str]:
    msgs: list[str] = []
    while True:
        try:
            ev = sink._queue.get_nowait()
        except Exception:
            break
        if ev[0] == "warning":
            msgs.append(ev[1]["message"])
    return msgs


async def test_main_executor_call_emits_guard_warning(ws):
    sink = QueueEventSink()
    reg = ToolRegistry()
    reg.register(FakePythonExecutor())
    llm = ScriptedLLM([
        [StreamChunk(tool_calls=[{"id": "tc1", "name": "python_executor",
                                   "args": {"code": "1+1"}}],
                      stop_reason="tool_use")],
        [StreamChunk(text="done"), StreamChunk(stop_reason="end_turn")],
    ])
    agent = AgentBase(
        name="main", agent_id="m-1", conv_id="c",
        system_prompt="s", llm=llm, tool_registry=reg,
        workspace=ws, memory_store=None,
        security=SecurityGate(workspace=ws), event_sink=sink,
        user_settings=None,
    )
    await agent.run(user_message="hi", memory_ids=[])
    msgs = await _collect_warnings(sink)
    assert any("python_executor" in m and "越级" in m for m in msgs), msgs


async def test_sub_agent_executor_call_does_not_warn(ws):
    # Sub Agent (name != "main") 正当使用 executor，不应触发越级警告。
    sink = QueueEventSink()
    reg = ToolRegistry()
    reg.register(FakePythonExecutor())
    llm = ScriptedLLM([
        [StreamChunk(tool_calls=[{"id": "tc1", "name": "python_executor",
                                   "args": {"code": "1+1"}}],
                      stop_reason="tool_use")],
        [StreamChunk(text="done"), StreamChunk(stop_reason="end_turn")],
    ])
    agent = AgentBase(
        name="file-agent", agent_id="fa-1", conv_id="c",
        system_prompt="s", llm=llm, tool_registry=reg,
        workspace=ws, memory_store=None,
        security=SecurityGate(workspace=ws), event_sink=sink,
        user_settings=None,
    )
    await agent.run(user_message="hi", memory_ids=[])
    msgs = await _collect_warnings(sink)
    assert not msgs


async def test_run_preserves_inherited_history(ws):
    # Regression: 之前 AgentBase.run 第一行无条件 self.message_history =
    # _build_initial_messages(...) 会把 DispatchTaskTool._inherit_history
    # 提前注入的对话历史**整段覆盖**，导致 inherit_agent_id 形同虚设。
    sink = QueueEventSink()
    reg = ToolRegistry()
    llm = ScriptedLLM([
        [StreamChunk(text="ok"), StreamChunk(stop_reason="end_turn")],
    ])
    agent = AgentBase(
        name="agent", agent_id="a-3", conv_id="c",
        system_prompt="SYS", llm=llm, tool_registry=reg,
        workspace=ws, memory_store=None,
        security=SecurityGate(workspace=ws), event_sink=sink,
        user_settings=None,
    )
    # 模拟 dispatch_task._inherit_history 注入历史
    agent.message_history = [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "old turn"},
        {"role": "assistant", "content": "old answer"},
    ]
    await agent.run(user_message="follow-up", memory_ids=[])
    # 旧历史保留，新 user 追加，未被重建覆盖
    assert agent.message_history[0]["content"] == "SYS"
    assert agent.message_history[1]["content"] == "old turn"
    assert agent.message_history[2]["content"] == "old answer"
    assert agent.message_history[3] == {"role": "user", "content": "follow-up"}


async def test_user_pref_injected_into_system_prompt(ws, tmp_path):
    # D 验证：MemoryStore 里 kind='user_pref' 的规则会自动出现在 system prompt。
    from openmarvis.memory.store import USER_PREF_CONV_ID, MemoryStore
    from openmarvis.store.db import create_engine, init_db
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    mem = MemoryStore(engine)
    await mem.put(conv_id=USER_PREF_CONV_ID, content="不要用 emoji",
                   kind="user_pref")
    sink = QueueEventSink()
    reg = ToolRegistry()
    llm = ScriptedLLM([
        [StreamChunk(text="ok"), StreamChunk(stop_reason="end_turn")],
    ])
    agent = AgentBase(
        name="agent", agent_id="x-1", conv_id="c",
        system_prompt="BASE", llm=llm, tool_registry=reg,
        workspace=ws, memory_store=mem,
        security=SecurityGate(workspace=ws), event_sink=sink,
        user_settings=None,
    )
    await agent.run(user_message="hi", memory_ids=[])
    sys_msg = agent.message_history[0]
    assert sys_msg["role"] == "system"
    assert "<user_preference_rules" in sys_msg["content"]
    assert "不要用 emoji" in sys_msg["content"]
    assert sys_msg["content"].startswith("BASE")  # 原 prompt 没被替换


async def test_user_pref_block_empty_when_no_rules(ws, tmp_path):
    from openmarvis.memory.store import MemoryStore
    from openmarvis.store.db import create_engine, init_db
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    sink = QueueEventSink()
    reg = ToolRegistry()
    llm = ScriptedLLM([
        [StreamChunk(text="ok"), StreamChunk(stop_reason="end_turn")],
    ])
    agent = AgentBase(
        name="agent", agent_id="x-2", conv_id="c",
        system_prompt="BASE", llm=llm, tool_registry=reg,
        workspace=ws, memory_store=MemoryStore(engine),
        security=SecurityGate(workspace=ws), event_sink=sink,
        user_settings=None,
    )
    await agent.run(user_message="hi", memory_ids=[])
    assert "<user_preference_rules" not in agent.message_history[0]["content"]


async def test_loop_iteration_limit(ws):
    sink = QueueEventSink()
    reg = ToolRegistry()
    reg.register(DummyTool())
    llm = ScriptedLLM([
        [StreamChunk(tool_calls=[{"id": f"tc{i}", "name": "double", "args": {"n": 1}}], stop_reason="tool_use")]
        for i in range(40)
    ])
    agent = AgentBase(
        name="agent", agent_id="a-2", conv_id="c",
        system_prompt="hi", llm=llm, tool_registry=reg,
        workspace=ws, memory_store=None,
        security=SecurityGate(workspace=ws), event_sink=sink,
        user_settings=None, max_iterations=5,
    )
    result = await agent.run(user_message="loop", memory_ids=[])
    assert result.status == "iteration_limit"
