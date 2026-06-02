from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BrowserSettings(BaseModel):
    headless: bool = False
    isolation_mode: Literal["shared", "per_conv"] = "shared"
    viewport_width: int = 1280
    viewport_height: int = 800
    default_timeout_ms: int = 10000
    allowed_domains: list[str] = Field(default_factory=list)
