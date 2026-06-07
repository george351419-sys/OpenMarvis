from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from ..store.sub_agents import SubAgentStore
from ..workspace.manager import Workspace
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


def _validate_attachment(path_str: str, workspace: Workspace) -> str | None:
    """Return None if path is OK, else a short reason string."""
    try:
        p = Path(path_str).expanduser()
    except (ValueError, OSError):
        return "无效路径"
    if not p.is_absolute():
        return "必须为绝对路径"
    # 必须真实存在
    if not p.exists():
        return "文件不存在"
    # 必须在 uploads_dir 内（防止注入任意系统路径作为 attachment）
    try:
        resolved = p.resolve()
        uploads = workspace.uploads_dir.resolve()
        if uploads != resolved and uploads not in resolved.parents:
            return f"必须位于 uploads 目录 ({uploads}) 内"
    except (OSError, RuntimeError):
        return "路径解析失败"
    return None


def parse_task_envelope(text: str, *, workspace: Workspace | None = None) -> TaskEnvelope:
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
    if workspace is not None:
        for raw in attachments:
            if (reason := _validate_attachment(raw, workspace)) is not None:
                raise ValueError(f"非法 attachment '{raw}': {reason}")
    return TaskEnvelope(overall_goal=overall, current_task=current, attachments=attachments)


class DispatchTaskArgs(BaseModel):
    agent_name: str = Field(description="目标 Sub Agent 名（file-agent / search-agent / browser / computer-agent / app-agent）")
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
        # 同一 conv 内 Sub Agent **串行执行** —— 多个 Sub Agent 共享同一
        # workspace / SubAgentStore / event_sink，并发会出竞态（如同名文件
        # 互相覆盖、SSE 事件顺序混乱）。锁按 conv_id 分桶，跨 conv 仍可并行。
        self._conv_locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, conv_id: str) -> asyncio.Lock:
        lock = self._conv_locks.get(conv_id)
        if lock is None:
            lock = asyncio.Lock()
            self._conv_locks[conv_id] = lock
        return lock

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
        if args.agent_name not in ("file-agent", "search-agent", "browser", "browser-agent",
                                    "computer-agent", "app-agent"):
            return ToolResult(error=f"未知 Sub Agent: {args.agent_name}")
        if len(args.memory_ids) > 20:
            return ToolResult(error="memory_ids 最多 20 条")
        try:
            parse_task_envelope(args.task, workspace=ctx.workspace)
        except ValueError as e:
            return ToolResult(error=str(e))

        async with self._lock_for(ctx.conv_id):
            return await self._run_under_lock(args, ctx)

    async def _run_under_lock(self, args: DispatchTaskArgs,
                                ctx: ToolContext) -> ToolResult:
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
