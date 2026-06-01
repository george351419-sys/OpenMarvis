from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from ..llm.event_sink import QueueEventSink
from ..memory.store import MemoryStore
from ..security.policy import SecurityGate
from ..tools.base import ToolContext, ToolResult
from ..tools.registry import ToolRegistry
from ..workspace.manager import Workspace


@dataclass
class AgentResult:
    status: str                          # ok / failed / iteration_limit
    final_content: str = ""
    summary: str = ""
    full_content: str = ""
    cards_json: str = "[]"


class AgentBase:
    def __init__(
        self,
        *,
        name: str,
        agent_id: str,
        conv_id: str,
        system_prompt: str,
        llm,
        tool_registry: ToolRegistry,
        workspace: Workspace,
        memory_store: MemoryStore | None,
        security: SecurityGate,
        event_sink: QueueEventSink,
        user_settings: Any,
        max_iterations: int = 30,
    ):
        self.name = name
        self.agent_id = agent_id
        self.conv_id = conv_id
        self.system_prompt = system_prompt
        self.llm = llm
        self.tools = tool_registry
        self.workspace = workspace
        self.memory = memory_store
        self.security = security
        self.sink = event_sink
        self.user_settings = user_settings
        self.max_iterations = max_iterations
        self.message_history: list[dict] = []

    def _ctx(self) -> ToolContext:
        return ToolContext(
            conv_id=self.conv_id, agent_id=self.agent_id,
            workspace=self.workspace, memory_store=self.memory,
            security=self.security, event_sink=self.sink,
            user_settings=self.user_settings,
        )

    async def _emit(self, event: str, data: dict) -> None:
        await self.sink.emit(event, data)

    async def _execute_tool(self, tc: dict) -> dict:
        tool = self.tools.get(tc["name"])
        if tool is None:
            return {"role": "tool", "tool_call_id": tc["id"],
                    "content": f"未知工具: {tc['name']}"}
        await self._emit("tool_call_start",
                         {"call_id": tc["id"], "name": tc["name"], "args": tc["args"]})
        try:
            parsed = tool.args_model.model_validate(tc["args"])
        except ValidationError as ve:
            err = f"参数校验失败: {ve.errors()}"
            await self._emit("tool_call_result",
                             {"call_id": tc["id"], "ok": False, "error": err})
            return {"role": "tool", "tool_call_id": tc["id"], "content": err}
        try:
            result: ToolResult = await tool.execute(parsed, self._ctx())
        except Exception as e:  # noqa: BLE001
            err = f"工具执行异常: {e}"
            await self._emit("tool_call_result",
                             {"call_id": tc["id"], "ok": False, "error": err})
            return {"role": "tool", "tool_call_id": tc["id"], "content": err}
        for card in result.cards:
            await self._emit("card", {"type": card.type, "payload": card.payload})
        preview = (result.content or "")[:300]
        await self._emit("tool_call_result",
                         {"call_id": tc["id"], "ok": result.error is None, "preview": preview})
        content = result.error or result.content
        if self.memory is not None and len(content) > 8192:
            mid = await self.memory.put(conv_id=self.conv_id, content=content)
            content = self.memory.summarize_preview(content, 400) + f"\n\n[memory_id: {mid}]"
        return {"role": "tool", "tool_call_id": tc["id"], "content": content}

    async def _build_initial_messages(self, user_message: str, memory_ids: list[str]) -> list[dict]:
        background = ""
        if memory_ids and self.memory is not None:
            records = await self.memory.fetch(memory_ids, conv_id=self.conv_id)
            if records:
                background = "\n\n## 背景信息\n" + "\n\n".join(
                    f"### [{r.id}]\n{r.content}" for r in records
                )
        return [
            {"role": "system", "content": self.system_prompt + background},
            {"role": "user", "content": user_message},
        ]

    async def _stream_one_turn(self) -> tuple[list[str], list[dict], str | None]:
        """Stream a single LLM turn; return (text_chunks, tool_calls, stop_reason)."""
        tools_schema = [t.anthropic_schema() for t in self.tools.for_agent(self.name)]
        current_text: list[str] = []
        current_tool_calls: list[dict] = []
        stop_reason: str | None = None
        async for chunk in self.llm.stream_chat(messages=self.message_history,
                                                tools=tools_schema):
            if chunk.thinking:
                await self._emit("thinking_delta", {"text": chunk.thinking})
            if chunk.text:
                await self._emit("content_delta", {"text": chunk.text})
                current_text.append(chunk.text)
            if chunk.tool_calls:
                current_tool_calls = chunk.tool_calls
            if chunk.stop_reason:
                stop_reason = chunk.stop_reason
        return current_text, current_tool_calls, stop_reason

    async def run(self, *, user_message: str, memory_ids: list[str]) -> AgentResult:
        self.message_history = await self._build_initial_messages(user_message, memory_ids)
        final_text_chunks: list[str] = []
        for _iteration in range(self.max_iterations):
            current_text, current_tool_calls, stop_reason = await self._stream_one_turn()
            assistant_msg: dict = {"role": "assistant",
                                   "content": "".join(current_text) or None}
            if current_tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])}}
                    for tc in current_tool_calls
                ]
            self.message_history.append(assistant_msg)
            final_text_chunks.append("".join(current_text))
            if stop_reason == "end_turn" or not current_tool_calls:
                final = "".join(final_text_chunks)
                return AgentResult(status="ok", final_content=final,
                                   summary=final[:200], full_content=final)
            for tc in current_tool_calls:
                tool_msg = await self._execute_tool(tc)
                self.message_history.append(tool_msg)
        await self._emit("error", {"message": "iteration_limit", "recoverable": False})
        return AgentResult(status="iteration_limit",
                           final_content="对话超出最大轮次")
