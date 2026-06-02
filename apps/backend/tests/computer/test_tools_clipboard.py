from unittest.mock import AsyncMock, patch

from openmarvis.computer.tools_clipboard import ClipboardReadTool, ClipboardWriteTool
from openmarvis.tools.base import ToolContext


def ctx():
    return ToolContext(conv_id="c", agent_id="sa-1", workspace=None,
                       memory_store=None, security=None, event_sink=None,
                       user_settings=None)


@patch("openmarvis.computer.tools_clipboard.run", new_callable=AsyncMock)
async def test_clipboard_read_plain(mock_run):
    mock_run.return_value = (0, "hello world")
    r = await ClipboardReadTool().execute(ClipboardReadTool.args_model(), ctx())
    assert "hello world" in r.content


@patch("openmarvis.computer.tools_clipboard.run", new_callable=AsyncMock)
async def test_clipboard_read_redacts_key(mock_run):
    mock_run.return_value = (0, "my key: sk-ant-12345678901234567890abcdefghij")
    r = await ClipboardReadTool().execute(ClipboardReadTool.args_model(), ctx())
    assert "sk-ant" not in r.content
    assert "[REDACTED]" in r.content
    assert "脱敏" in r.content


@patch("openmarvis.computer.tools_clipboard.run", new_callable=AsyncMock)
async def test_clipboard_write(mock_run):
    mock_run.return_value = (0, "")
    r = await ClipboardWriteTool().execute(
        ClipboardWriteTool.args_model(text="hello"), ctx())
    assert r.error is None
