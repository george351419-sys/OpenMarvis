from __future__ import annotations


def test_list_skills_includes_builtin_document_convert(client):
    r = client.get("/skills")
    assert r.status_code == 200
    rows = r.json()
    names = [m["name"] for m in rows]
    assert "document_convert" in names
    doc = next(m for m in rows if m["name"] == "document_convert")
    assert doc["risk"] == "medium"
    assert "source_path" in doc["params"]
    assert doc["params"]["source_path"]["required"] is True
    assert "exec.shell" in doc["allowed_tools"]
