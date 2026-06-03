from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from litellm import acompletion

_FINISH_REASON_MAP = {"stop": "end_turn", "tool_calls": "tool_use", "length": "max_tokens"}


@dataclass
class StreamChunk:
    text: str = ""
    thinking: str = ""
    tool_calls: list[dict] = field(default_factory=list)   # [{id, name, args}]
    stop_reason: str | None = None                         # end_turn / tool_use / max_tokens


def _accumulate_tool_deltas(
    tool_deltas: list[dict], accumulated: dict[int, dict]
) -> None:
    for td in tool_deltas:
        idx = td.get("index", 0)
        acc = accumulated.setdefault(idx, {"id": "", "name": "", "args_str": ""})
        if td.get("id"):
            acc["id"] = td["id"]
        fn = td.get("function", {}) or {}
        if fn.get("name"):
            acc["name"] = fn["name"]
        if fn.get("arguments"):
            acc["args_str"] += fn["arguments"]


def _resolve_finish(
    finish: str | None, accumulated: dict[int, dict]
) -> tuple[str | None, list[dict]]:
    stop_reason = _FINISH_REASON_MAP.get(finish or "")
    tcs: list[dict] = []
    if finish == "tool_calls":
        for acc in accumulated.values():
            try:
                parsed = json.loads(acc["args_str"]) if acc["args_str"] else {}
            except json.JSONDecodeError:
                parsed = {"__raw__": acc["args_str"]}
            tcs.append({"id": acc["id"], "name": acc["name"], "args": parsed})
    return stop_reason, tcs


class LiteLLMClient:
    def __init__(self, *, model: str, api_key: str | None = None,
                 max_tokens: int = 4096, temperature: float = 0.2):
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def stream_chat(self, *, messages: list[dict], tools: list[dict],
                          ) -> AsyncIterator[StreamChunk]:
        params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }
        if tools:
            params["tools"] = [{"type": "function", "function": t} for t in tools]
        if self.api_key:
            params["api_key"] = self.api_key

        accumulated_tool_calls: dict[int, dict] = {}

        stream = await acompletion(**params)
        async for chunk in stream:
            choice = chunk["choices"][0]
            delta = choice.get("delta", {}) or {}
            text = delta.get("content") or ""
            thinking = delta.get("reasoning_content") or ""
            _accumulate_tool_deltas(delta.get("tool_calls") or [], accumulated_tool_calls)
            stop_reason, tcs = _resolve_finish(choice.get("finish_reason"), accumulated_tool_calls)
            yield StreamChunk(text=text, thinking=thinking, tool_calls=tcs, stop_reason=stop_reason)

    async def complete_with_image(self, *, prompt: str, image_path: str) -> str:
        """一次性视觉请求；返回模型纯文本响应。"""
        import base64
        from pathlib import Path
        b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
        import litellm
        resp = await litellm.acompletion(
            model=self.model,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url",
                      "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }],
        )
        return (resp.choices[0].message.content or "").strip()
