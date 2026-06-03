from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class VisionLocateError(RuntimeError):
    """LLM 返回无法解析为坐标。"""


_PROMPT = """你是一个 GUI 控件定位助手。任务：在给定屏幕截图中定位 "{query}"。
返回 JSON：{{"x": <int 像素>, "y": <int 像素>, "confidence": <0~1>}}。
坐标系：图片左上角为原点，向右 +x，向下 +y。
不要包含任何额外文字，只返回 JSON。
"""


_JSON_RE = re.compile(r'\{[^{}]*"x"\s*:\s*\d+[^{}]*"y"\s*:\s*\d+[^{}]*\}')


class VisionBackend:
    def __init__(self, llm: Any):
        self.llm = llm

    async def locate(self, query: str, image_path: str | Path) -> tuple[int, int]:
        prompt = _PROMPT.format(query=query)
        resp = await self.llm.complete_with_image(prompt=prompt,
                                                    image_path=str(image_path))
        m = _JSON_RE.search(resp or "")
        if not m:
            raise VisionLocateError(f"no JSON coords in LLM response: {resp!r}")
        try:
            obj = json.loads(m.group(0))
            return int(obj["x"]), int(obj["y"])
        except (ValueError, KeyError, TypeError) as e:
            raise VisionLocateError(f"parse failed: {e}") from e
