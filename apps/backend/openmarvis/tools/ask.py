from __future__ import annotations

import asyncio
from typing import Literal

import ulid
from pydantic import BaseModel, Field

from .base import Tool, ToolContext, ToolResult


class Option(BaseModel):
    label: str | None = None
    description: str | None = None
    file_path: str | None = None
    package_name: str | None = None


class AskUserArgs(BaseModel):
    title: str
    form_type: Literal["single_select", "multi_select", "confirm"] = "single_select"
    display_type: Literal["text", "image", "file", "app"] = "text"
    options: list[Option] = Field(default_factory=list)


class PendingAskRegistry:
    def __init__(self):
        self._pending: dict[str, asyncio.Future] = {}

    def create(self) -> tuple[str, asyncio.Future]:
        ask_id = f"ask_{ulid.new().str.lower()}"
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[ask_id] = fut
        return ask_id, fut

    async def resolve(self, ask_id: str, choices: list[str]) -> None:
        fut = self._pending.pop(ask_id, None)
        if fut and not fut.done():
            fut.set_result(choices)


class AskUserTool(Tool):
    name = "ask_user"
    description = "向用户发起交互式询问（高危确认、推断失败兜底）。"
    args_model = AskUserArgs
    risk_level = "low"
    available_to = ("main",)

    def __init__(self, registry: PendingAskRegistry):
        self.registry = registry

    async def execute(self, args: AskUserArgs, ctx: ToolContext) -> ToolResult:
        ask_id, fut = self.registry.create()
        payload = {
            "ask_id": ask_id,
            "title": args.title,
            "form_type": args.form_type,
            "display_type": args.display_type,
            "options": [o.model_dump() for o in args.options],
        }
        await ctx.event_sink.emit("ask_user", payload)
        choices = await fut
        return ToolResult(content=f"用户选择: {choices}")
