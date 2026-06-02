from __future__ import annotations

import json

from pydantic import BaseModel, Field

from ..tools.base import Tool, ToolContext, ToolResult
from ._subprocess import run


class SystemInfoArgs(BaseModel):
    verbose: bool = False


class SystemInfoTool(Tool):
    name = "system_info"
    description = "macOS 系统信息摘要（verbose=true 返回原始 JSON）"
    args_model = SystemInfoArgs
    risk_level = "low"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args: SystemInfoArgs, ctx: ToolContext) -> ToolResult:
        code, out = await run(["system_profiler",
                                "SPHardwareDataType", "SPSoftwareDataType",
                                "SPDisplaysDataType", "-json"],
                                timeout=15)
        if code != 0:
            return ToolResult(error=f"system_profiler failed: {out[:200]}")
        if args.verbose:
            return ToolResult(content=out[:50000])
        try:
            data = json.loads(out)
            hw = data.get("SPHardwareDataType", [{}])[0]
            sw = data.get("SPSoftwareDataType", [{}])[0]
            disp = data.get("SPDisplaysDataType", [{}])[0]
            summary = (
                f"========================\n"
                f"macOS {sw.get('os_version','?')}, {hw.get('machine_model','?')}\n"
                f"CPU: {hw.get('chip_type','?')}, {hw.get('number_processors','?')} 核\n"
                f"内存: {hw.get('physical_memory','?')}\n"
                f"显示器: {disp.get('_name','?')}\n"
                f"========================"
            )
            return ToolResult(content=summary)
        except json.JSONDecodeError:
            return ToolResult(content=out[:1000])


class DiskUsageArgs(BaseModel):
    path: str = "/"


class DiskUsageTool(Tool):
    name = "disk_usage"
    description = "df -h 查看磁盘使用"
    args_model = DiskUsageArgs
    risk_level = "low"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args: DiskUsageArgs, ctx: ToolContext) -> ToolResult:
        code, out = await run(["df", "-h", args.path], timeout=10)
        return ToolResult(content=out if code == 0 else f"error: {out[:200]}")


class ListProcessesArgs(BaseModel):
    top_n: int = Field(default=20)
    sort_by: str = Field(default="cpu", description="cpu | mem")


class ListProcessesTool(Tool):
    name = "list_processes"
    description = "ps aux 排序取前 N"
    args_model = ListProcessesArgs
    risk_level = "low"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args: ListProcessesArgs, ctx: ToolContext) -> ToolResult:
        code, out = await run(["ps", "aux"], timeout=10)
        if code != 0:
            return ToolResult(error=f"ps failed: {out[:200]}")
        lines = out.splitlines()
        header, rows = lines[0], lines[1:]
        col = 2 if args.sort_by == "cpu" else 3

        def _sort_key(line):
            parts = line.split()
            try:
                return -float(parts[col])
            except (IndexError, ValueError):
                return 0.0

        rows.sort(key=_sort_key)
        return ToolResult(content="\n".join([header] + rows[: args.top_n]))


class FindProcessArgs(BaseModel):
    name_pattern: str


class FindProcessTool(Tool):
    name = "find_process"
    description = "pgrep -fl 查找进程"
    args_model = FindProcessArgs
    risk_level = "low"
    available_to = ("computer-agent",)
    skip_cmd_guard = True

    async def execute(self, args: FindProcessArgs, ctx: ToolContext) -> ToolResult:
        code, out = await run(["pgrep", "-fl", args.name_pattern], timeout=5)
        if code == 1:  # pgrep returns 1 when no match
            return ToolResult(content="(no matches)")
        if code != 0:
            return ToolResult(error=f"pgrep failed: {out[:200]}")
        return ToolResult(content=out.strip() or "(no matches)")
