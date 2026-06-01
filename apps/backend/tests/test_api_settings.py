from __future__ import annotations


def test_get_settings_returns_defaults(client):
    r = client.get("/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["llm"]["provider_model"]
    assert body["security"]["level"] in ("strict", "normal", "permissive")


def test_put_settings_updates_security_level(client):
    r = client.put("/settings", json={"security": {"level": "strict"}})
    assert r.status_code == 200
    assert r.json()["security"]["level"] == "strict"
