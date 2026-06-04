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

    _EXECUTOR_TOOLS = ("python_executor", "shell_executor")
    _SUB_AGENT_HINT = {
        "python_executor": "文件/数据处理类任务建议派 file-agent；系统操作类派 computer-agent",
        "shell_executor": "文件类派 file-agent；系统操作类派 computer-agent",
    }

    async def _emit_executor_guard(self, tool_name: str) -> None:
        if self.name != "main" or tool_name not in self._EXECUTOR_TOOLS:
            return
        await self._emit("warning", {
            "message": f"Main 直接调用 {tool_name}（越级）。{self._SUB_AGENT_HINT[tool_name]}",
        })

    async def _execute_tool(self, tc: dict) -> dict:
        tool = self.tools.get(tc["name"])
        if tool is None:
            return {"role": "tool", "tool_call_id": tc["id"],
                    "content": f"未知工具: {tc['name']}"}
        await self._emit_executor_guard(tc["name"])
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

    async def _resolve_user_pref_block(self) -> str:
        """Pull all kind='user_pref' MemoryEntries and format for system prompt injection."""
        if self.memory is None:
            return ""
        rules = await self.memory.fetch_user_prefs(limit=50)
        if not rules:
            return ""
        body = "\n".join(f"- [{r.id}] {r.content}" for r in rules)
        return (
            "\n\n<user_preference_rules>\n"
            "以下是用户在历次会话中沉淀的长期偏好规则；除非用户当下明确要求例外，"
            "全部遵守。删除某条用 `forget_user_preference(pref_id=...)`。\n"
            f"{body}\n"
            "</user_preference_rules>"
        )

    async def _build_initial_messages(self, user_message: str, memory_ids: list[str]) -> list[dict]:
        background = ""
        if memory_ids and self.memory is not None:
            records = await self.memory.fetch(memory_ids, conv_id=self.conv_id)
            if records:
                background = "\n\n## 背景信息\n" + "\n\n".join(
                    f"### [{r.id}]\n{r.content}" for r in records
                )
        prefs = await self._resolve_user_pref_block()
        return [
            {"role": "system", "content": self.system_prompt + prefs + background},
            {"role": "user", "content": user_message},
        ]

    async def _resolve_memory_background(self, memory_ids: list[str]) -> str:
        if not memory_ids or self.memory is None:
            return ""
        records = await self.memory.fetch(memory_ids, conv_id=self.conv_id)
        if not records:
            return ""
        return "\n\n## 背景信息\n" + "\n\n".join(
            f"### [{r.id}]\n{r.content}" for r in records
        )

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
        if self.message_history:
            # 续接：保留 inherit_agent_id 注入的历史，只追加新 user 轮次。
            bg = await self._resolve_memory_background(memory_ids)
            self.message_history.append(
                {"role": "user", "content": user_message + bg}
            )
        else:
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
