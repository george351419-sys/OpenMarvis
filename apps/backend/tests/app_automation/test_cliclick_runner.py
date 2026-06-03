from __future__ import annotations

import pytest

from openmarvis.app_automation.cliclick_runner import (
    CliclickError,
    CliclickRunner,
)


@pytest.mark.asyncio
async def test_click_invokes_subprocess(monkeypatch):
    seen: dict = {}

    async def fake_run(cmd, *, timeout=5):
        seen["cmd"] = list(cmd)
        return 0, ""

    monkeypatch.setattr("openmarvis.app_automation.cliclick_runner._run", fake_run)
    r = CliclickRunner(bin_path="/usr/local/bin/cliclick")
    await r.click(120, 240)
    assert seen["cmd"] == ["/usr/local/bin/cliclick", "c:120,240"]


@pytest.mark.asyncio
async def test_type_text_invokes_subprocess(monkeypatch):
    seen: dict = {}

    async def fake_run(cmd, *, timeout=5):
        seen["cmd"] = list(cmd)
        return 0, ""

    monkeypatch.setattr("openmarvis.app_automation.cliclick_runner._run", fake_run)
    r = CliclickRunner(bin_path="/usr/local/bin/cliclick")
    await r.type_text("hello")
    assert seen["cmd"] == ["/usr/local/bin/cliclick", "t:hello"]


@pytest.mark.asyncio
async def test_nonzero_exit_raises(monkeypatch):
    async def fake_run(cmd, *, timeout=5):
        return 1, "boom"
    monkeypatch.setattr("openmarvis.app_automation.cliclick_runner._run", fake_run)
    r = CliclickRunner(bin_path="/usr/local/bin/cliclick")
    with pytest.raises(CliclickError):
        await r.click(1, 1)
