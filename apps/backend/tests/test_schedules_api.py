from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_list_schedules_starts_empty(client):
    r = client.get("/schedules")
    assert r.status_code == 200
    assert r.json() == []


def test_list_schedules_returns_created(client):
    mgr = client.app.state.om.scheduler_manager
    run_at = datetime.now(UTC) + timedelta(days=1)
    sid = mgr.add_once(run_at, instruction="hi", description="d",
                        origin_conv_id="conv_x")

    r = client.get("/schedules")
    assert r.status_code == 200
    rows = r.json()
    assert any(row["id"] == sid for row in rows)
    row = next(row for row in rows if row["id"] == sid)
    assert row["trigger_type"] == "once"
    assert row["description"] == "d"
    assert row["origin_conv_id"] == "conv_x"


def test_delete_schedule_ok_then_404(client):
    mgr = client.app.state.om.scheduler_manager
    run_at = datetime.now(UTC) + timedelta(days=1)
    sid = mgr.add_once(run_at, instruction="x", description="",
                        origin_conv_id="c")

    r = client.delete(f"/schedules/{sid}")
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    r2 = client.delete(f"/schedules/{sid}")
    assert r2.status_code == 404
