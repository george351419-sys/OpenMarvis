"""ListSkillsTool：枚举可见 skill，让 LLM 不必 hallucinate skill 名。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from openmarvis.skill.registry import SkillRegistry
from openmarvis.skill.tools_skill import ListSkillsArgs, ListSkillsTool

_BUILTINS = Path(__file__).resolve().parents[2] / "openmarvis" / "skill" / "builtins"


@pytest.fixture
def populated_registry():
    reg = SkillRegistry()
    reg.scan(_BUILTINS)
    return reg


@pytest.fixture
def ctx():
    c = MagicMock()
    return c


async def test_list_skills_empty_registry(ctx):
    tool = ListSkillsTool(skill_registry=SkillRegistry())
    r = await tool.execute(ListSkillsArgs(), ctx)
    assert r.error is None
    assert "没有可见的 Skill" in r.content


async def test_list_skills_summary_mode_returns_markdown_table(populated_registry, ctx):
    tool = ListSkillsTool(skill_registry=populated_registry)
    r = await tool.execute(ListSkillsArgs(), ctx)
    assert r.error is None
    # Markdown 表头
    assert "| skill | risk | 描述 |" in r.content
    # 6 个 builtin 都应出现
    for name in ("document_convert", "file_organizer", "pdf",
                  "document_writer", "excel_processing",
                  "planning_with_files"):
        assert f"`{name}`" in r.content


async def test_list_skills_detail_mode_returns_json_with_params(populated_registry, ctx):
    tool = ListSkillsTool(skill_registry=populated_registry)
    r = await tool.execute(ListSkillsArgs(detail=True), ctx)
    assert r.error is None
    # 详细模式给的是 JSON
    import json
    data = json.loads(r.content)
    assert isinstance(data, list)
    names = {item["name"] for item in data}
    assert "pdf" in names
    # 每个条目带 params 字典
    pdf_entry = next(it for it in data if it["name"] == "pdf")
    assert "params" in pdf_entry
    assert "action" in pdf_entry["params"]
    # action 是 enum
    assert "enum" in pdf_entry["params"]["action"]
    assert "extract" in pdf_entry["params"]["action"]["enum"]
    # required 字段也带出来
    assert pdf_entry["params"]["action"]["required"] is True


async def test_list_skills_sorted_by_name(populated_registry, ctx):
    tool = ListSkillsTool(skill_registry=populated_registry)
    r = await tool.execute(ListSkillsArgs(), ctx)
    # 提取每行的 skill name，按出现顺序
    lines = [l for l in r.content.splitlines() if l.startswith("| `")]
    names = [l.split("`")[1] for l in lines]
    assert names == sorted(names)
