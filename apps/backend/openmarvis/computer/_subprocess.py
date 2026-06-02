from __future__ import annotations

import asyncio
from collections.abc import Sequence


async def run(cmd: Sequence[str], *, timeout: float = 30.0,
              env: dict[str, str] | None = None) -> tuple[int, str]:
    """Run a subprocess; return (exit_code, stdout_merged_with_stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        return -1, "timeout"
    return proc.returncode or 0, (out or b"").decode("utf-8", errors="replace")


async def osascript(script: str, *, timeout: float = 10.0) -> tuple[int, str]:
    return await run(["osascript", "-e", script], timeout=timeout)
