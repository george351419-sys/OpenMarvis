from unittest.mock import AsyncMock, patch

from openmarvis.computer.tools_info import (
    DiskUsageTool,
    FindProcessTool,
    ListProcessesTool,
    SystemInfoTool,
)
from openmarvis.tools.base import ToolContext


def make_ctx():
    return ToolContext(conv_id="c", agent_id="sa-1", workspace=None,
                       memory_store=None, security=None, event_sink=None,
                       user_settings=None)


@patch("openmarvis.computer.tools_info.run", new_callable=AsyncMock)
async def test_system_info_summary(mock_run):
    mock_run.return_value = (0, '{"SPHardwareDataType":[{"machine_model":"MacBookPro18,2"}]}')
    tool = SystemInfoTool()
    r = await tool.execute(SystemInfoTool.args_model(verbose=False), make_ctx())
    assert r.content
    assert r.error is None


@patch("openmarvis.computer.tools_info.run", new_callable=AsyncMock)
async def test_system_info_verbose_returns_json(mock_run):
    json_payload = '{"SPHardwareDataType":[{"a":"b"}]}'
    mock_run.return_value = (0, json_payload)
    tool = SystemInfoTool()
    r = await tool.execute(SystemInfoTool.args_model(verbose=True), make_ctx())
    assert json_payload in r.content


@patch("openmarvis.computer.tools_info.run", new_callable=AsyncMock)
async def test_disk_usage(mock_run):
    mock_run.return_value = (0, "Filesystem  Size  Used  Avail\n/dev/disk1  1Ti   500G  500G")
    tool = DiskUsageTool()
    r = await tool.execute(DiskUsageTool.args_model(), make_ctx())
    assert "500G" in r.content


@patch("openmarvis.computer.tools_info.run", new_callable=AsyncMock)
async def test_list_processes(mock_run):
    mock_run.return_value = (0,
        "USER     PID %CPU %MEM   VSZ   RSS TTY      STAT   COMMAND\n"
        "bessie   123 10.0  2.0 100000 50000 ?        S      python3 main.py\n"
        "bessie   124  5.0  1.0 100000 50000 ?        S      sleep 10\n")
    tool = ListProcessesTool()
    r = await tool.execute(ListProcessesTool.args_model(top_n=10), make_ctx())
    assert "python3" in r.content


@patch("openmarvis.computer.tools_info.run", new_callable=AsyncMock)
async def test_find_process(mock_run):
    mock_run.return_value = (0, "456 python3 server.py")
    tool = FindProcessTool()
    r = await tool.execute(FindProcessTool.args_model(name_pattern="python3"), make_ctx())
    assert "456" in r.content
