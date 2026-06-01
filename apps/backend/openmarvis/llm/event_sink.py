from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

_SENTINEL = object()


class QueueEventSink:
    """异步队列封装：Agent 侧 emit；API 侧 drain 推 SSE。"""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()

    async def emit(self, event: str, data: dict) -> None:
        await self._queue.put((event, data))

    async def close(self) -> None:
        await self._queue.put(_SENTINEL)

    async def drain(self) -> AsyncIterator[tuple[str, dict]]:
        while True:
            item = await self._queue.get()
            if item is _SENTINEL:
                return
            yield item
