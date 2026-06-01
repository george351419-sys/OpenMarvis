from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatch(BaseModel):
    llm: dict | None = None
    security: dict | None = None
    workspace: dict | None = None


@router.get("")
async def get_settings(request: Request) -> dict:
    s = request.app.state.om.settings
    return {
        "llm": s.llm.model_dump(),
        "security": s.security.model_dump(),
        "workspace": {"root": str(s.workspace.root),
                       "max_total_gb": s.workspace.max_total_gb,
                       "max_per_conv_mb": s.workspace.max_per_conv_mb},
    }


@router.put("")
async def update_settings(patch: SettingsPatch, request: Request) -> dict:
    s = request.app.state.om.settings
    if patch.llm:
        for k, v in patch.llm.items():
            if hasattr(s.llm, k):
                setattr(s.llm, k, v)
    if patch.security:
        for k, v in patch.security.items():
            if hasattr(s.security, k):
                setattr(s.security, k, v)
    return await get_settings(request)
