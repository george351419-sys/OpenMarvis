from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


@router.get("/echo")
async def echo(message: str) -> EventSourceResponse:
    async def gen() -> AsyncIterator[dict]:
        for ch in message:
            yield {"data": json.dumps({"char": ch})}
            await asyncio.sleep(0)
        yield {"data": json.dumps({"done": True})}

    return EventSourceResponse(gen())
