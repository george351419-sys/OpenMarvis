from __future__ import annotations

from pydantic import BaseModel, Field

from ..store.sub_agents import SubAgentStore
from .base import Card, Tool, ToolContext, ToolResult


class PresentResultArgs(BaseModel):
    agent_id: str = Field(description="要展示的 Sub Agent ID（来自 dispatch_task 返回）")


class PresentResultTool(Tool):
    name = "present_result"
    description = "展示指定 Sub Agent 的完整执行结果作为最终回复。"
    args_model = PresentResultArgs
    risk_level = "low"
    available_to = ("main",)

    def __init__(self, sub_store: SubAgentStore):
        self.sub_store = sub_store

    async def execute(self, args: PresentResultArgs, ctx: ToolContext) -> ToolResult:
        full = await self.sub_store.get_full(agent_id=args.agent_id, conv_id=ctx.conv_id)
        if full is None:
            return ToolResult(error=f"未找到 Sub Agent {args.agent_id} 的结果")
        cards = [Card(type=c.get("type", ""), payload=c.get("payload", ""))
                 for c in (full.get("cards") or [])]
        return ToolResult(content=full["full_content"], cards=cards)
