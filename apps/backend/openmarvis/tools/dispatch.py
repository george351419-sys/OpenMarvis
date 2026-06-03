from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from ..store.sub_agents import SubAgentStore
from .base import Tool, ToolContext, ToolResult

if TYPE_CHECKING:
    from ..agents.base import AgentResult

_RE_GOAL = re.compile(r"<overall_goal>(.*?)</overall_goal>", re.DOTALL)
_RE_TASK = re.compile(r"<current_task>(.*?)</current_task>", re.DOTALL)
_RE_ATTACH = re.compile(r"<attachments>(.*?)</attachments>", re.DOTALL)


@dataclass
class TaskEnvelope:
    overall_goal: str
    current_task: str
    attachments: list[str]


def parse_task_envelope(text: str) -> TaskEnvelope:
    g = _RE_GOAL.search(text)
    t = _RE_TASK.search(text)
    if not g or not t:
        raise ValueError("task 必须包含 <overall_goal> 与 <current_task> 标签")
    overall = g.group(1).strip()
    current = t.group(1).strip()
    attachments: list[str] = []
    a = _RE_ATTACH.search(text)
    if a:
        for line in a.group(1).splitlines():
            line = line.strip()
            if line:
                attachments.append(line)
    if not overall or not current:
        raise ValueError("<overall_goal> 与 <current_task> 不可为空")
    return TaskEnvelope(overall_goal=overall, current_task=current, attachments=attachments)


class DispatchTaskArgs(BaseModel):
    agent_name: str = Field(description="目标 Sub Agent 名（file-agent / search-agent / browser-agent / computer-agent / app-agent）")
    task: str = Field(description="结构化任务（<overall_goal>...</overall_goal><current_task>...</current_task>）")
    memory_ids: list[str] = Field(default_factory=list, description="最多 20 条历史 memory_xxx")
    inherit_agent_id: str = Field(default="", description="可选：继承同 conv 已完成同名 Sub Agent")


async def _run_sub_agent(sub, *, task: str,
                          memory_ids: list[str]) -> AgentResult:
    return await sub.run(user_message=task, memory_ids=memory_ids)


class DispatchTaskTool(Tool):
    name = "dispatch_task"
    description = "把任务派发给 Sub Agent 自主执行。"
    args_model = DispatchTaskArgs
    risk_level = "low"
    available_to = ("main",)

    def __init__(self, factory, sub_store: SubAgentStore):
        self.factory = factory
        self.sub_store = sub_store

    async def _inherit_history(self, sub, args: DispatchTaskArgs, ctx: ToolContext) -> None:
        if not args.inherit_agent_id:
            return
        msgs = await self.sub_store.try_inherit(
            target_agent_name=args.agent_name,
            source_id=args.inherit_agent_id,
            conv_id=ctx.conv_id,
        )
        if msgs:
            sub.message_history = msgs

    async def _persist(self, sub, *, args: DispatchTaskArgs,
                        result: AgentResult, ctx: ToolContext) -> None:
        import json as _json

        await self.sub_store.save(
            agent_id=sub.agent_id,
            conv_id=ctx.conv_id,
            agent_name=sub.name,
            status=result.status,
            input_task=args.task,
            summary=result.summary,
            full_content=result.full_content,
            messages_json=_json.dumps(sub.message_history, ensure_ascii=False),
            cards_json=result.cards_json,
        )

    async def execute(self, args: DispatchTaskArgs, ctx: ToolContext) -> ToolResult:
        if args.agent_name not in ("file-agent", "search-agent", "browser-agent",
                                    "computer-agent", "app-agent"):
            return ToolResult(error=f"未知 Sub Agent: {args.agent_name}")
        if len(args.memory_ids) > 20:
            return ToolResult(error="memory_ids 最多 20 条")
        try:
            parse_task_envelope(args.task)
        except ValueError as e:
            return ToolResult(error=str(e))

        sub = self.factory.build(
            agent_name=args.agent_name,
            conv_id=ctx.conv_id,
            workspace=ctx.workspace,
            memory_store=ctx.memory_store,
            security=ctx.security,
            event_sink=ctx.event_sink,
            user_settings=ctx.user_settings,
        )

        await self._inherit_history(sub, args, ctx)

        await ctx.event_sink.emit("sub_agent_start",
                                  {"agent_id": sub.agent_id, "agent_name": sub.name})
        result = await _run_sub_agent(sub, task=args.task, memory_ids=args.memory_ids)
        await ctx.event_sink.emit("sub_agent_end",
                                  {"agent_id": sub.agent_id, "status": result.status})

        await self._persist(sub, args=args, result=result, ctx=ctx)

        memory_id = None
        if ctx.memory_store and len(result.full_content) > 8192:
            memory_id = await ctx.memory_store.put(conv_id=ctx.conv_id,
                                                    content=result.full_content)
        body = (f"Agent ID: {sub.agent_id}\n\nStatus: {result.status}\n\n"
                f"Summary: {result.summary[:400]}")
        return ToolResult(content=body, memory_id=memory_id)
