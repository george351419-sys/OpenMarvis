"""planning_with_files skill 静态校验。"""
from __future__ import annotations

from pathlib import Path

import pytest

from openmarvis.skill.manifest import load_skill
from openmarvis.skill.registry import SkillRegistry

_BUILTINS = Path(__file__).resolve().parents[2] / "openmarvis" / "skill" / "builtins"
_SKILL = _BUILTINS / "planning_with_files"


def test_planning_skill_loads():
    m = load_skill(_SKILL)
    assert m.name == "planning_with_files"
    assert m.risk == "medium"
    assert m.params["goal"].required is True
    assert m.params["items"].required is True
    # resume / max_iterations 都是可选
    assert m.params["resume"].required is False
    assert m.params["max_iterations"].required is False


def test_planning_skill_validates_params():
    m = load_skill(_SKILL)
    out = m.validate_params({"goal": "summarize", "items": ["/x/a.pdf"]})
    assert out["goal"] == "summarize"

    with pytest.raises(ValueError, match="missing required"):
        m.validate_params({"items": ["/x"]})


def test_planning_skill_prompt_has_state_machine_and_resume():
    m = load_skill(_SKILL)
    p = m.prompt
    # 关键状态名
    assert "pending" in p
    assert "in_progress" in p
    assert "done" in p
    assert "failed" in p
    # 必须含 plan.json 持久化纪律
    assert "plan.json" in p or "plan_path" in p
    # 必须含恢复语义
    assert "resume" in p.lower() or "续跑" in p or "续传" in p


def test_planning_skill_allowed_tools_broad_but_no_delete():
    m = load_skill(_SKILL)
    # 需要广泛能力（处理各种 item）
    for must in ("read_file", "write_file", "python_executor", "edit_file"):
        assert must in m.allowed_tools, f"missing {must}"
    # 但严禁 delete
    assert "delete" not in m.allowed_tools


def test_all_six_skills_picked_up():
    """6 个内置 skill 都应被扫到。"""
    reg = SkillRegistry()
    reg.scan(_BUILTINS)
    names = {m.name for m in reg.list()}
    assert {
        "document_convert", "file_organizer", "pdf",
        "document_writer", "excel_processing", "planning_with_files",
    } <= names
