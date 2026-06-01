from __future__ import annotations


def test_create_list_delete_conversation(client):
    r = client.post("/conversations", json={"title": "first"})
    assert r.status_code == 200
    conv_id = r.json()["id"]

    r2 = client.get("/conversations")
    assert any(c["id"] == conv_id for c in r2.json())

    r3 = client.delete(f"/conversations/{conv_id}")
    assert r3.status_code == 200

    r4 = client.get("/conversations")
    assert all(c["id"] != conv_id for c in r4.json())


def test_get_messages_empty_for_new_conv(client):
    conv_id = client.post("/conversations", json={"title": "t"}).json()["id"]
    r = client.get(f"/conversations/{conv_id}/messages")
    assert r.status_code == 200
    assert r.json() == []
