import json


def test_echo_sse_streams_message_chars(client):
    with client.stream("GET", "/echo?message=hi") as response:
        assert response.status_code == 200
        events: list[dict] = []
        for line in response.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[len("data:"):].strip()))
    chars = [e["char"] for e in events if "char" in e]
    assert "".join(chars) == "hi"
    assert events[-1] == {"done": True}
