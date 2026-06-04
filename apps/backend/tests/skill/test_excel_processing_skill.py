"""excel_processing skill 静态校验。"""
from __future__ import annotations

from pathlib import Path

import pytest

from openmarvis.skill.manifest import load_skill
from openmarvis.skill.registry import SkillRegistry

_BUILTINS = Path(__file__).resolve().parents[2] / "openmarvis" / "skill" / "builtins"
_SKILL = _BUILTINS / "excel_processing"


def test_excel_skill_loads():
    m = load_skill(_SKILL)
    assert m.name == "excel_processing"
    assert m.risk == "medium"
    assert m.params["action"].required is True
    assert m.params["action"].enum == ["inspect", "transform", "merge"]
    assert m.params["sources"].required is True
    # recipe 是可选 object 类型
    assert m.params["recipe"].required is False
    assert m.params["recipe"].type == "object"


def test_excel_skill_validates_params():
    m = load_skill(_SKILL)
    out = m.validate_params({"action": "inspect",
                              "sources": ["/x/a.xlsx"]})
    assert out["action"] == "inspect"

    with pytest.raises(ValueError, match="must be one of"):
        m.validate_params({"action": "delete", "sources": ["/x"]})

    with pytest.raises(ValueError, match="missing required"):
        m.validate_params({"sources": ["/x"]})


def test_excel_skill_prompt_has_three_actions_and_pandas_templates():
    m = load_skill(_SKILL)
    p = m.prompt
    for action in ("inspect", "transform", "merge"):
        assert action in p
    # 必须含 pandas 代码模板
    assert "import pandas" in p
    assert "mv-product" in p


def test_excel_skill_allowed_tools_restrict_to_safe_set():
    m = load_skill(_SKILL)
    assert "python_executor" in m.allowed_tools
    assert "write_file" in m.allowed_tools
    # delete / shell 不在
    assert "delete" not in m.allowed_tools
    assert "shell_executor" not in m.allowed_tools


def test_all_five_skills_picked_up_by_registry():
    """五个内置 skill 都应被 scan 扫到：
    document_convert / file_organizer / pdf / document_writer / excel_processing
    """
    reg = SkillRegistry()
    n = reg.scan(_BUILTINS)
    names = {m.name for m in reg.list()}
    assert {
        "document_convert", "file_organizer", "pdf",
        "document_writer", "excel_processing",
    } <= names
    assert n >= 5
