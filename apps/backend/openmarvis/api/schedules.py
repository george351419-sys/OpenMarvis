from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("")
async def list_schedules(request: Request) -> list[dict]:
    mgr = getattr(request.app.state.om, "scheduler_manager", None)
    if mgr is None:
        return []
    return [
        {
            "id": r.id,
            "origin_conv_id": r.origin_conv_id,
            "trigger_type": r.trigger_type,
            "trigger_spec": r.trigger_spec,
            "instruction": r.instruction,
            "description": r.description,
            "next_run_at": r.next_run_at.isoformat() if r.next_run_at else None,
        }
        for r in mgr.list()
    ]


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str, request: Request) -> dict:
    mgr = getattr(request.app.state.om, "scheduler_manager", None)
    if mgr is None or not mgr.cancel(schedule_id):
        raise HTTPException(status_code=404, detail="schedule not found")
    return {"ok": True}
