from __future__ import annotations

import asyncio
import shutil


class CliclickError(RuntimeError):
    """cliclick 未安装 / 调用失败。"""


async def _run(cmd, *, timeout: float = 5.0) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        return -1, "timeout"
    return proc.returncode or 0, (out or b"").decode("utf-8", errors="replace")


def _default_bin() -> str | None:
    return shutil.which("cliclick")


class CliclickRunner:
    def __init__(self, bin_path: str | None = None):
        self.bin = bin_path or _default_bin()

    def _require_bin(self) -> str:
        if not self.bin:
            raise CliclickError("cliclick not installed — brew install cliclick")
        return self.bin

    async def click(self, x: int, y: int) -> None:
        bin_ = self._require_bin()
        code, out = await _run([bin_, f"c:{int(x)},{int(y)}"])
        if code != 0:
            raise CliclickError(f"cliclick click failed: {out.strip()}")

    async def type_text(self, text: str) -> None:
        bin_ = self._require_bin()
        code, out = await _run([bin_, f"t:{text}"])
        if code != 0:
            raise CliclickError(f"cliclick type failed: {out.strip()}")
