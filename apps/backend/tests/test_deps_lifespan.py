from fastapi.testclient import TestClient

from openmarvis.main import create_app


def test_app_lifespan_initializes_db_and_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENMARVIS_WORKSPACE__ROOT", str(tmp_path / "om"))
    app = create_app()
    with TestClient(app) as c:
        r = c.get("/healthz")
        assert r.status_code == 200
    assert (tmp_path / "om" / "data.db").exists()
