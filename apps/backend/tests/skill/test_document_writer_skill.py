"""document_writer skill 静态校验。"""
from __future__ import annotations

from pathlib import Path

import pytest

from openmarvis.skill.manifest import load_skill
from openmarvis.skill.registry import SkillRegistry

_BUILTINS = Path(__file__).resolve().parents[2] / "openmarvis" / "skill" / "builtins"
_SKILL = _BUILTINS / "document_writer"


def test_document_writer_loads():
    m = load_skill(_SKILL)
    assert m.name == "document_writer"
    assert m.risk == "medium"
    assert m.params["sources"].required is True
    assert m.params["doc_type"].enum == ["report", "summary", "comparison", "proposal"]


def test_document_writer_validates_params():
    m = load_skill(_SKILL)
    out = m.validate_params({"sources": ["/x/a.pdf"]})
    assert out["sources"] == ["/x/a.pdf"]

    # doc_type 越界
    with pytest.raises(ValueError, match="must be one of"):
        m.validate_params({"sources": ["/x"], "doc_type": "novel"})

    # 缺 sources
    with pytest.raises(ValueError, match="missing required"):
        m.validate_params({"doc_type": "report"})


def test_document_writer_prompt_has_four_stages_and_anti_hallucination():
    m = load_skill(_SKILL)
    p = m.prompt
    assert "读取" in p
    assert "大纲" in p
    assert "撰写" in p
    assert "输出" in p
    # 反幻觉条款
    assert "杜撰" in p or "幻觉" in p
    assert "mv-product" in p


def test_document_writer_allowed_tools_include_read_file_and_convert():
    m = load_skill(_SKILL)
    assert "read_file" in m.allowed_tools
    assert "convert_file" in m.allowed_tools
    assert "write_file" in m.allowed_tools
    # 严禁的工具不应在白名单
    assert "delete" not in m.allowed_tools
    assert "shell_executor" not in m.allowed_tools


def test_document_writer_picked_up_by_registry():
    reg = SkillRegistry()
    reg.scan(_BUILTINS)
    assert "document_writer" in {m.name for m in reg.list()}
