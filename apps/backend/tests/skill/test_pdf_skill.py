"""pdf skill 静态校验：manifest + prompt + 注册被 Registry 扫到。"""
from __future__ import annotations

from pathlib import Path

import pytest

from openmarvis.skill.manifest import load_skill
from openmarvis.skill.registry import SkillRegistry

_BUILTINS = Path(__file__).resolve().parents[2] / "openmarvis" / "skill" / "builtins"
_PDF = _BUILTINS / "pdf"


def test_pdf_skill_loads():
    m = load_skill(_PDF)
    assert m.name == "pdf"
    assert m.risk == "medium"
    # action 必填、enum 三选一
    assert m.params["action"].required is True
    assert m.params["action"].enum == ["extract", "split", "merge"]
    # source_paths 必填
    assert m.params["source_paths"].required is True


def test_pdf_skill_validates_params():
    m = load_skill(_PDF)
    out = m.validate_params({"action": "extract",
                              "source_paths": ["/x/a.pdf"]})
    assert out["action"] == "extract"

    with pytest.raises(ValueError, match="must be one of"):
        m.validate_params({"action": "weird", "source_paths": ["/x"]})

    with pytest.raises(ValueError, match="missing required"):
        m.validate_params({"action": "extract"})


def test_pdf_skill_prompt_has_all_three_actions():
    m = load_skill(_PDF)
    p = m.prompt
    assert "extract" in p
    assert "split" in p
    assert "merge" in p
    # 必须含产物声明纪律
    assert "mv-product" in p


def test_pdf_skill_picked_up_by_registry():
    reg = SkillRegistry()
    reg.scan(_BUILTINS)
    names = {m.name for m in reg.list()}
    # 现在内置 3 个：document_convert / file_organizer / pdf
    assert "pdf" in names
    assert {"document_convert", "file_organizer", "pdf"} <= names
