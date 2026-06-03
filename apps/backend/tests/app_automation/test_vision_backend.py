from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from openmarvis.app_automation.vision_backend import VisionBackend, VisionLocateError


@pytest.mark.asyncio
async def test_locate_parses_coords_from_llm(monkeypatch, tmp_path):
    img = tmp_path / "shot.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    fake_llm = MagicMock()
    async def fake_complete(*a, **kw):
        return json.dumps({"x": 320, "y": 480, "confidence": 0.9})
    fake_llm.complete_with_image = fake_complete

    vb = VisionBackend(llm=fake_llm)
    coords = await vb.locate("发送按钮", img)
    assert coords == (320, 480)


@pytest.mark.asyncio
async def test_locate_raises_on_malformed_response(monkeypatch, tmp_path):
    img = tmp_path / "shot.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    fake_llm = MagicMock()
    async def fake_complete(*a, **kw):
        return "I cannot locate it"
    fake_llm.complete_with_image = fake_complete
    vb = VisionBackend(llm=fake_llm)
    with pytest.raises(VisionLocateError):
        await vb.locate("发送按钮", img)
