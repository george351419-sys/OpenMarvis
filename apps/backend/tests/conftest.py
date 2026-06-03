from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openmarvis.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("OPENMARVIS_WORKSPACE__ROOT", str(tmp_path / "om"))
    with TestClient(create_app()) as c:
        yield c
