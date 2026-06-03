from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from playwright.async_api import Playwright, async_playwright

from .settings import BrowserSettings


class BrowserPool:
    """Manages Playwright BrowserContext objects.

    - `shared` mode: single context reused across all conv_ids
    - `per_conv` mode: a dict {conv_id: context}
    """

    def __init__(self, *, settings: BrowserSettings, profile_dir_base: Path):
        self.settings = settings
        self.profile_dir_base = Path(profile_dir_base)
        self._playwright: Playwright | None = None
        self._contexts: dict[str, Any] = {}        # key = "_shared" or conv_id
        self._lock = asyncio.Lock()

    def is_started(self) -> bool:
        return self._playwright is not None

    def _profile_dir_for(self, conv_id: str) -> Path:
        if self.settings.isolation_mode == "shared":
            return self.profile_dir_base / "shared"
        return self.profile_dir_base / "per_conv" / conv_id

    async def _ensure_started(self) -> None:
        async with self._lock:
            if self._playwright is None:
                self._playwright = await async_playwright().start()

    async def _get_or_make_context(self, conv_id: str):
        key = "_shared" if self.settings.isolation_mode == "shared" else conv_id
        if key in self._contexts:
            return self._contexts[key]
        await self._ensure_started()
        assert self._playwright is not None      # _ensure_started 保证
        profile_dir = self._profile_dir_for(conv_id)
        profile_dir.mkdir(parents=True, exist_ok=True)
        context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=self.settings.headless,
            viewport={"width": self.settings.viewport_width,
                       "height": self.settings.viewport_height},
        )
        self._contexts[key] = context
        return context

    async def get_page(self, conv_id: str):
        context = await self._get_or_make_context(conv_id)
        page = await context.new_page()
        page.set_default_timeout(self.settings.default_timeout_ms)
        return page

    async def shutdown(self) -> None:
        for ctx in self._contexts.values():
            try:
                await ctx.close()
            except Exception:  # noqa: BLE001
                pass
        self._contexts.clear()
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:  # noqa: BLE001
                pass
            self._playwright = None
