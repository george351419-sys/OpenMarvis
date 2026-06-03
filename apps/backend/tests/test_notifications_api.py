from __future__ import annotations

import time

from sqlmodel import Session

from openmarvis.store.models import ScheduleNotification


def _seed(engine, *, origin_conv_id: str, summary: str, read: bool = False) -> int:
    with Session(engine) as s:
        n = ScheduleNotification(
            origin_conv_id=origin_conv_id, schedule_id="sch_test",
            virtual_conv_id="sched_virt", summary=summary,
            status="success", read=read, created_at=int(time.time()),
        )
        s.add(n)
        s.commit()
        s.refresh(n)
        return n.id


def test_unread_lists_only_unread(client, tmp_path, monkeypatch):
    engine = client.app.state.om.engine
    _seed(engine, origin_conv_id="conv_a", summary="hello unread")
    read_id = _seed(engine, origin_conv_id="conv_a", summary="already read",
                     read=True)

    r = client.get("/notifications/unread")
    assert r.status_code == 200
    summaries = [n["summary"] for n in r.json()]
    assert "hello unread" in summaries
    assert "already read" not in summaries
    assert read_id not in [n["id"] for n in r.json()]


def test_unread_filters_by_origin_conv(client):
    engine = client.app.state.om.engine
    _seed(engine, origin_conv_id="conv_a", summary="for a")
    _seed(engine, origin_conv_id="conv_b", summary="for b")

    r = client.get("/notifications/unread", params={"origin_conv_id": "conv_a"})
    assert r.status_code == 200
    items = r.json()
    assert all(n["origin_conv_id"] == "conv_a" for n in items)
    assert any(n["summary"] == "for a" for n in items)


def test_mark_read_flips_flag_and_404_when_missing(client):
    engine = client.app.state.om.engine
    nid = _seed(engine, origin_conv_id="conv_c", summary="to mark")

    r = client.post(f"/notifications/{nid}/read")
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    follow = client.get("/notifications/unread",
                          params={"origin_conv_id": "conv_c"})
    assert all(n["id"] != nid for n in follow.json())

    miss = client.post("/notifications/99999/read")
    assert miss.status_code == 404
