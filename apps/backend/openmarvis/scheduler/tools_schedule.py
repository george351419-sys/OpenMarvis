from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..tools.base import Card, Tool, ToolContext, ToolResult


class CreateScheduleArgs(BaseModel):
    trigger_type: Literal["once", "interval", "cron"]
    trigger_spec: str = Field(description="once: ISO datetime；interval: 秒数；cron: 5 段 crontab")
    instruction: str
    description: str = ""
    origin_conv_id: str


class CreateScheduleTool(Tool):
    name = "create_schedule"
    description = "创建定时任务。once 用 ISO datetime（UTC 或带时区），interval 用秒数 ≥ 60，cron 用 5 段表达式。"
    args_model = CreateScheduleArgs
    risk_level = "medium"
    available_to = ("main",)

    async def execute(self, args: CreateScheduleArgs, ctx: ToolContext) -> ToolResult:
        mgr = ctx.user_settings.scheduler_manager
        if mgr is None:
            return ToolResult(error="scheduler_not_initialized")
        safe_instruction = ctx.security.credential_guard.mask(args.instruction)
        try:
            if args.trigger_type == "once":
                try:
                    run_at = datetime.fromisoformat(args.trigger_spec)
                except ValueError as e:
                    return ToolResult(error=f"bad trigger_spec (need ISO datetime): {e}")
                sid = mgr.add_once(run_at, instruction=safe_instruction,
                                    description=args.description,
                                    origin_conv_id=args.origin_conv_id)
            elif args.trigger_type == "interval":
                try:
                    secs = int(args.trigger_spec)
                except ValueError as e:
                    return ToolResult(error=f"bad trigger_spec (need integer seconds): {e}")
                sid = mgr.add_interval(every_seconds=secs,
                                        instruction=safe_instruction,
                                        description=args.description,
                                        origin_conv_id=args.origin_conv_id)
            else:                                  # cron
                sid = mgr.add_cron(expr=args.trigger_spec,
                                    instruction=safe_instruction,
                                    description=args.description,
                                    origin_conv_id=args.origin_conv_id)
        except Exception as e:
            return ToolResult(error=f"create_schedule_failed: {e}")
        card = Card(
            type="mv-schedule-created",
            payload=json.dumps({"schedule_id": sid,
                                  "trigger_type": args.trigger_type,
                                  "trigger_spec": args.trigger_spec,
                                  "description": args.description},
                                 ensure_ascii=False),
        )
        return ToolResult(content=f"schedule_created: {sid}", cards=[card])


class ListSchedulesArgs(BaseModel):
    pass


class ListSchedulesTool(Tool):
    name = "list_schedules"
    description = "列出全部已注册定时任务。"
    args_model = ListSchedulesArgs
    risk_level = "low"
    available_to = ("main",)

    async def execute(self, args: ListSchedulesArgs, ctx: ToolContext) -> ToolResult:
        mgr = ctx.user_settings.scheduler_manager
        if mgr is None:
            return ToolResult(error="scheduler_not_initialized")
        rows = mgr.list()
        data = [{"id": r.id, "trigger_type": r.trigger_type,
                  "trigger_spec": r.trigger_spec,
                  "description": r.description,
                  "next_run_at": str(r.next_run_at) if r.next_run_at else None}
                 for r in rows]
        return ToolResult(content=json.dumps(data, ensure_ascii=False))


class CancelScheduleArgs(BaseModel):
    schedule_id: str


class CancelScheduleTool(Tool):
    name = "cancel_schedule"
    description = "按 schedule_id 取消已注册定时任务。"
    args_model = CancelScheduleArgs
    risk_level = "medium"
    available_to = ("main",)

    async def execute(self, args: CancelScheduleArgs, ctx: ToolContext) -> ToolResult:
        mgr = ctx.user_settings.scheduler_manager
        if mgr is None:
            return ToolResult(error="scheduler_not_initialized")
        ok = mgr.cancel(args.schedule_id)
        if not ok:
            return ToolResult(error=f"cancel_failed: schedule {args.schedule_id} not found")
        return ToolResult(content=f"cancelled: {args.schedule_id}")
