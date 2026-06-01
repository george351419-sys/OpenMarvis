from pydantic import BaseModel, Field

from openmarvis.tools.base import Tool, ToolContext, ToolResult
from openmarvis.tools.registry import ToolRegistry


class EchoArgs(BaseModel):
    text: str = Field(description="待回显文本")


class EchoTool(Tool):
    name = "echo"
    description = "回显输入文本"
    args_model = EchoArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    async def execute(self, args: EchoArgs, ctx: ToolContext) -> ToolResult:
        return ToolResult(content=args.text)


def test_registry_filters_by_agent():
    reg = ToolRegistry()
    reg.register(EchoTool())
    main_tools = reg.for_agent("main")
    file_tools = reg.for_agent("file-agent")
    search_tools = reg.for_agent("search-agent")
    assert {t.name for t in main_tools} == {"echo"}
    assert {t.name for t in file_tools} == {"echo"}
    assert search_tools == []


def test_to_anthropic_schema_shape():
    reg = ToolRegistry()
    reg.register(EchoTool())
    schemas = reg.anthropic_schemas("main")
    assert schemas[0]["name"] == "echo"
    assert schemas[0]["description"].startswith("回显")
    assert "text" in schemas[0]["input_schema"]["properties"]


async def test_tool_executes_with_args():
    tool = EchoTool()
    ctx = ToolContext(conv_id="c", agent_id="a", workspace=None, memory_store=None,
                       security=None, event_sink=None, user_settings=None)
    result = await tool.execute(EchoArgs(text="hi"), ctx)
    assert result.content == "hi"
