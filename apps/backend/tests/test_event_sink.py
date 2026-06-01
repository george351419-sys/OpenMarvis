import pytest

from openmarvis.llm.event_sink import QueueEventSink


@pytest.mark.asyncio
async def test_emit_and_drain_in_order():
    sink = QueueEventSink()
    await sink.emit("content_delta", {"text": "a"})
    await sink.emit("content_delta", {"text": "b"})
    await sink.close()
    out = [e async for e in sink.drain()]
    assert [e[0] for e in out] == ["content_delta", "content_delta"]
    assert out[1][1]["text"] == "b"
