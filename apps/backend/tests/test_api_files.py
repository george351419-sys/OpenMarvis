import io


def test_upload_creates_workspace_file(client):
    conv = client.post("/conversations", json={"title": "t"}).json()
    files = {"file": ("hello.txt", io.BytesIO(b"hi there"), "text/plain")}
    r = client.post(f"/files/upload?conv_id={conv['id']}", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body[0]["original_name"] == "hello.txt"
    assert "uploads/" in body[0]["saved_path"]


def test_preview_rejects_outside_path(client):
    r = client.get("/files/preview?path=/etc/passwd")
    assert r.status_code == 403
