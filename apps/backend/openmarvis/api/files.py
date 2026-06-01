from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from ..workspace.manager import Workspace

router = APIRouter(prefix="/files", tags=["files"])


def _safe_name(name: str) -> str:
    return Path(name).name.replace("\\", "_").replace("/", "_") or "file.bin"


@router.post("/upload")
async def upload(conv_id: str, request: Request, file: UploadFile) -> list[dict]:
    workspaces = request.app.state.om.workspaces
    ws: Workspace = workspaces.get_or_create(conv_id)
    target = ws.uploads_dir / _safe_name(file.filename or "file.bin")
    data = await file.read()
    target.write_bytes(data)
    return [{"original_name": file.filename, "saved_path": str(target),
             "size": len(data)}]


def _path_allowed(path: Path, state) -> bool:
    p = path.expanduser().resolve()
    ws_root = state.settings.workspace.root.expanduser().resolve() / "workspaces"
    return ws_root == p or ws_root in p.parents


@router.get("/preview")
async def preview(path: str, request: Request):
    p = Path(path)
    if not _path_allowed(p, request.app.state.om):
        raise HTTPException(403, "path not allowed")
    if not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p)


@router.get("/download")
async def download(path: str, request: Request):
    p = Path(path)
    if not _path_allowed(p, request.app.state.om):
        raise HTTPException(403, "path not allowed")
    if not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p, filename=p.name)
