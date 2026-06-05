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


# ---------------- purge / cleanup ----------------


def test_purge_hard_deletes_conv_and_messages(client):
    """purge 后 conv 应该从 DB 里彻底消失，连 archived list 都看不到。"""
    conv_id = client.post("/conversations", json={"title": "to-purge"}).json()["id"]
    r = client.post(f"/conversations/{conv_id}/purge")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["purged"]["Conversation"] == 1
    # purge 后再访问 messages —— 仍可返回 []（因为 messages 也已删）
    r2 = client.get(f"/conversations/{conv_id}/messages")
    assert r2.json() == []


def test_purge_unknown_id_returns_404(client):
    r = client.post("/conversations/conv_does_not_exist/purge")
    assert r.status_code == 404


def test_cleanup_dry_run_does_not_delete(client):
    """default dry_run=true 应只统计、不真删。"""
    a = client.post("/conversations", json={"title": "t"}).json()["id"]
    b = client.post("/conversations", json={"title": "real-name"}).json()["id"]
    r = client.post("/conversations/cleanup",
                     json={"empty_title": True, "dry_run": True})
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is True
    # 'real-name' 不算空 title；'t' 算（len(trim) == 1）
    assert body["would_purge"] >= 1
    assert a in body["sample_ids"]
    # 真没删
    r2 = client.get("/conversations")
    ids = {c["id"] for c in r2.json()}
    assert a in ids and b in ids


def test_cleanup_real_purge_removes_matching(client):
    """dry_run=False 时确实删除；不匹配的留下。"""
    a = client.post("/conversations", json={"title": ""}).json()["id"]
    b = client.post("/conversations", json={"title": "t"}).json()["id"]
    c = client.post("/conversations", json={"title": "重要会话"}).json()["id"]
    r = client.post("/conversations/cleanup",
                     json={"empty_title": True, "dry_run": False})
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is False
    assert body["purged"] >= 2
    # 重要会话还在
    ids = {x["id"] for x in client.get("/conversations").json()}
    assert c in ids
    assert a not in ids and b not in ids


def test_cleanup_max_messages_filter(client):
    """max_messages=0 应只删没消息的会话。"""
    empty_conv = client.post("/conversations", json={"title": "empty"}).json()["id"]
    used_conv = client.post("/conversations", json={"title": "used"}).json()["id"]

    # 给 used_conv 写一条 Message
    from openmarvis.store.models import Message
    from sqlmodel import Session
    engine = client.app.state.om.engine
    with Session(engine) as s:
        s.add(Message(conv_id=used_conv, role="user", content="hi"))
        s.commit()

    r = client.post("/conversations/cleanup",
                     json={"max_messages": 0, "dry_run": True})
    body = r.json()
    assert empty_conv in body["sample_ids"]
    assert used_conv not in body["sample_ids"]


def test_cleanup_combined_filters_apply_and(client):
    """多个 filter 同时存在时是 AND，不是 OR。"""
    # 空标题 + 有消息 → 不该被清
    keep = client.post("/conversations", json={"title": ""}).json()["id"]
    from openmarvis.store.models import Message
    from sqlmodel import Session
    engine = client.app.state.om.engine
    with Session(engine) as s:
        s.add(Message(conv_id=keep, role="user", content="x"))
        s.commit()

    # 空标题 + 无消息 → 应清
    drop = client.post("/conversations", json={"title": ""}).json()["id"]

    r = client.post("/conversations/cleanup",
                     json={"empty_title": True, "max_messages": 0,
                            "dry_run": True})
    sample = r.json()["sample_ids"]
    assert drop in sample
    assert keep not in sample
