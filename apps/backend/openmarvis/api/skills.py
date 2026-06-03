from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
async def list_skills(request: Request) -> list[dict]:
    reg = getattr(request.app.state.om, "skill_registry", None)
    if reg is None:
        return []
    return [
        {
            "name": m.name,
            "version": m.version,
            "description": m.description,
            "author": m.author,
            "license": m.license,
            "risk": m.risk,
            "params": {
                pname: {
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "enum": p.enum,
                    "default": p.default,
                }
                for pname, p in m.params.items()
            },
            "allowed_tools": m.allowed_tools,
        }
        for m in reg.list()
    ]
