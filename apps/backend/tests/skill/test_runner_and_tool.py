from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from openmarvis.skill.manifest import SkillManifest, SkillParam
from openmarvis.skill.registry import SkillRegistry
from openmarvis.skill.runner import build_skill_registry, render_skill_prompt
from openmarvis.skill.tools_skill import UseSkillArgs, UseSkillTool
from openmarvis.tools.base import Tool
from openmarvis.tools.registry import ToolRegistry


class _Stub(Tool):
    name = "x"
    description = ""
    args_model = MagicMock
    available_to = ("main",)


def test_build_skill_registry_filters_by_allowlist():
    parent = ToolRegistry()
    a = _Stub(); a.name = "fs.read_file"
    b = _Stub(); b.name = "fs.write_file"
    c = _Stub(); c.name = "exec.shell"
    for t in (a, b, c):
        parent.register(t)
    reg = build_skill_registry(parent, ["fs.read_file", "exec.shell"])
    names = {t.name for t in reg.all()}
    assert names == {"fs.read_file", "exec.shell"}
    # SkillToolRegistry exposes all on for_agent regardless of available_to
    assert {t.name for t in reg.for_agent("skill:any")} == names


def test_render_skill_prompt_substitutes_placeholders():
    m = SkillManifest(name="doc",
                      params={"src": SkillParam(type="string", required=True)})
    m.prompt = "convert {{src}} via {{params}}"
    out = render_skill_prompt(m, {"src": "/tmp/a.md"})
    assert "/tmp/a.md" in out
    assert "{{src}}" not in out
    assert "{'src': '/tmp/a.md'}" in out


@pytest.mark.asyncio
async def test_use_skill_tool_unknown_skill_returns_error():
    skills = SkillRegistry()
    parent = ToolRegistry()
    tool = UseSkillTool(skill_registry=skills, parent_tool_registry=parent)
    ctx = MagicMock()
    res = await tool.execute(UseSkillArgs(name="missing", params={}), ctx)
    assert res.error and "未知" in res.error


@pytest.mark.asyncio
async def test_use_skill_tool_invokes_runner_for_known_skill(monkeypatch):
    skills = SkillRegistry()
    manifest = SkillManifest(name="echo", risk="low", allowed_tools=[])
    manifest.prompt = "do it"
    skills._items["echo"] = manifest                    # bypass scan
    parent = ToolRegistry()
    tool = UseSkillTool(skill_registry=skills, parent_tool_registry=parent)

    # Patch run_skill to avoid spinning a real AgentBase
    called = {}
    async def fake_run_skill(**kw):
        called.update(kw)
        out = MagicMock()
        out.final_content = "ok"
        out.status = "ok"
        return out
    monkeypatch.setattr("openmarvis.skill.tools_skill.run_skill", fake_run_skill)

    ctx = MagicMock()
    res = await tool.execute(UseSkillArgs(name="echo", params={}), ctx)
    assert res.error is None
    assert res.content == "ok"
    assert called["manifest"].name == "echo"
    assert res.cards[0].type == "skill_call"


def test_assess_risk_returns_manifest_risk():
    skills = SkillRegistry()
    m = SkillManifest(name="big", risk="medium")
    skills._items["big"] = m
    tool = UseSkillTool(skill_registry=skills, parent_tool_registry=ToolRegistry())
    r = tool.assess_risk(UseSkillArgs(name="big", params={}), None)
    assert r.level == "medium"
