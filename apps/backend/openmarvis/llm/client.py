from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from litellm import acompletion
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

logger = logging.getLogger(__name__)

# 这些错误可重试：限流、上游 5xx、网络抖动。AuthenticationError / BadRequest
# 故意不在内 — 这些重试无意义，会浪费时间还掩盖配置 bug。
_RETRYABLE_EXC: tuple[type[Exception], ...] = (
    RateLimitError,
    InternalServerError,
    ServiceUnavailableError,
    APIConnectionError,
    Timeout,
    APIError,  # litellm 把上游未分类错误包装成这个
)
_RETRY_MAX = 3
_RETRY_BASE_SECONDS = 2.0  # 指数退避：2s, 4s, 8s


async def _acompletion_with_retries(**params: Any) -> Any:
    """对 litellm.acompletion 套上限流重试 + 退避。

    流式请求只能在 *建立连接* 这一步重试 —— 一旦开始流，部分 token 已发出去就
    不能再重来了。所以本函数只把第一次 acompletion 调用纳入重试范围；调用方拿
    到流后自己处理流中错误。
    """
    delay = _RETRY_BASE_SECONDS
    last: Exception | None = None
    for attempt in range(_RETRY_MAX + 1):
        try:
            return await acompletion(**params)
        except _RETRYABLE_EXC as e:
            last = e
            if attempt >= _RETRY_MAX:
                break
            logger.warning("LLM retryable error (attempt %d/%d): %s; sleep %.1fs",
                           attempt + 1, _RETRY_MAX, type(e).__name__, delay)
            await asyncio.sleep(delay)
            delay *= 2
    assert last is not None
    raise last

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
                 max_tokens: int = 4096, temperature: float = 0.2,
                 vision_model: str | None = None,
                 api_base: str | None = None):
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        # 若主模型不支持视觉（如 DeepSeek），单独走 vision_model。None 时复用 model。
        self.vision_model = vision_model or model
        # OpenAI 兼容端点（如混元），传给 litellm acompletion。
        self.api_base = api_base

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
        if self.api_base:
            params["api_base"] = self.api_base

        accumulated_tool_calls: dict[int, dict] = {}

        stream = await _acompletion_with_retries(**params)
        async for chunk in stream:
            choice = chunk["choices"][0]
            delta = choice.get("delta", {}) or {}
            text = delta.get("content") or ""
            thinking = delta.get("reasoning_content") or ""
            _accumulate_tool_deltas(delta.get("tool_calls") or [], accumulated_tool_calls)
            stop_reason, tcs = _resolve_finish(choice.get("finish_reason"), accumulated_tool_calls)
            yield StreamChunk(text=text, thinking=thinking, tool_calls=tcs, stop_reason=stop_reason)

    async def complete_with_image(self, *, prompt: str, image_path: str) -> str:
        """一次性视觉请求；返回模型纯文本响应。走 vision_model。"""
        import base64
        from pathlib import Path
        b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
        resp = await _acompletion_with_retries(
            model=self.vision_model,
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
