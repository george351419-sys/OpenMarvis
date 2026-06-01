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
