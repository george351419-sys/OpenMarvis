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
