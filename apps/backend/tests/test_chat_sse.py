import json

from openmarvis.agents.base import AgentResult


def test_chat_sse_streams_content_and_done(client, monkeypatch):
    class FakeAgent:
        async def run(self, *, user_message, memory_ids):
            await self.sink.emit("content_delta", {"text": "hello"})
            return AgentResult(status="ok", final_content="hello",
                               summary="hello", full_content="hello")

    def fake_build_main_agent(**kw):
        a = FakeAgent()
        a.sink = kw["event_sink"]
        return a

    monkeypatch.setattr("openmarvis.api.chat.build_main_agent", fake_build_main_agent)

    conv = client.post("/conversations", json={"title": "t"}).json()
    payload = {"conv_id": conv["id"], "message": "hi", "attachments": []}
    events: list[tuple[str, dict]] = []
    last_event = None
    with client.stream("POST", "/chat", json=payload) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                last_event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                events.append((last_event, json.loads(line[len("data:"):].strip())))
    types = [e[0] for e in events]
    assert "content_delta" in types
    assert "done" in types
