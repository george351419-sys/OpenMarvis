import pytest
from litellm.exceptions import AuthenticationError, RateLimitError

from openmarvis.llm.client import LiteLLMClient, StreamChunk


async def test_stream_chat_yields_text_chunks(monkeypatch):
    async def fake_acompletion(**kwargs):
        async def gen():
            yield {"choices": [{"delta": {"content": "hel"}}]}
            yield {"choices": [{"delta": {"content": "lo"}}]}
            yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}
        return gen()

    monkeypatch.setattr("openmarvis.llm.client.acompletion", fake_acompletion)
    client = LiteLLMClient(model="claude-opus-4-7", api_key="fake")
    chunks: list[StreamChunk] = []
    async for c in client.stream_chat(messages=[{"role": "user", "content": "hi"}], tools=[]):
        chunks.append(c)
    text = "".join(c.text for c in chunks if c.text)
    assert text == "hello"
    assert any(c.stop_reason == "end_turn" for c in chunks)


async def test_stream_chat_tool_use_collected(monkeypatch):
    async def fake_acompletion(**kwargs):
        async def gen():
            yield {"choices": [{"delta": {
                "tool_calls": [{"index": 0, "id": "tc_1",
                               "function": {"name": "read_text",
                                            "arguments": '{"file_path":"/a"}'}}]
            }}]}
            yield {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}
        return gen()
    monkeypatch.setattr("openmarvis.llm.client.acompletion", fake_acompletion)
    client = LiteLLMClient(model="claude-opus-4-7", api_key="fake")
    last = None
    async for c in client.stream_chat(messages=[], tools=[]):
        last = c
    assert last.stop_reason == "tool_use"
    assert last.tool_calls and last.tool_calls[0]["name"] == "read_text"


async def test_stream_chat_retries_on_rate_limit(monkeypatch):
    # 第 1、2 次抛 RateLimitError；第 3 次正常返回 stream。
    calls = {"n": 0}

    async def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimitError("rate limited", llm_provider="openai", model="x")

        async def gen():
            yield {"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]}
        return gen()

    # 把睡眠时间打成 0，避免测试慢
    monkeypatch.setattr("openmarvis.llm.client._RETRY_BASE_SECONDS", 0.0)
    monkeypatch.setattr("openmarvis.llm.client.acompletion", flaky)
    client = LiteLLMClient(model="x", api_key="fake")
    chunks: list[StreamChunk] = []
    async for c in client.stream_chat(messages=[], tools=[]):
        chunks.append(c)
    assert calls["n"] == 3  # 重试了 2 次后第 3 次成功
    assert "".join(c.text for c in chunks if c.text) == "ok"


async def test_stream_chat_does_not_retry_auth_error(monkeypatch):
    # AuthenticationError 不可恢复，应立即抛、不要浪费时间重试。
    calls = {"n": 0}

    async def auth_fail(**kwargs):
        calls["n"] += 1
        raise AuthenticationError("bad key", llm_provider="openai", model="x")

    monkeypatch.setattr("openmarvis.llm.client._RETRY_BASE_SECONDS", 0.0)
    monkeypatch.setattr("openmarvis.llm.client.acompletion", auth_fail)
    client = LiteLLMClient(model="x", api_key="fake")
    with pytest.raises(AuthenticationError):
        async for _ in client.stream_chat(messages=[], tools=[]):
            pass
    assert calls["n"] == 1  # 没重试
