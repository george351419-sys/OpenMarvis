"""file_organizer skill 落盘后 manifest 与 prompt 的最低正确性。

这是一个新内置 skill；纯静态验证：
- skill.yaml 能被 SkillRegistry 扫到
- params 校验对 source_dir / by / dry_run 合理
- prompt 含关键阶段词
"""
from __future__ import annotations

from pathlib import Path

import pytest

from openmarvis.skill.manifest import load_skill
from openmarvis.skill.registry import SkillRegistry

_BUILTINS = Path(__file__).resolve().parents[2] / "openmarvis" / "skill" / "builtins"
_FILE_ORG = _BUILTINS / "file_organizer"


def test_file_organizer_loads_from_disk():
    m = load_skill(_FILE_ORG)
    assert m.name == "file_organizer"
    assert m.risk == "medium"
    # 必填 source_dir
    assert m.params["source_dir"].required is True
    # by 接 enum 限制
    assert m.params["by"].enum == ["type", "date", "project"]


def test_file_organizer_validates_params():
    m = load_skill(_FILE_ORG)
    # 最小合法：只给 source_dir，其余走默认（缺省值 None / 由 prompt 决定）
    out = m.validate_params({"source_dir": "/Users/me/Downloads"})
    assert out["source_dir"] == "/Users/me/Downloads"

    # by 枚举越界
    with pytest.raises(ValueError, match="must be one of"):
        m.validate_params({"source_dir": "/x", "by": "weird"})

    # source_dir 必填
    with pytest.raises(ValueError, match="missing required"):
        m.validate_params({"by": "type"})


def test_file_organizer_prompt_has_four_stages():
    m = load_skill(_FILE_ORG)
    p = m.prompt
    # 必须有"四阶段"字样和具体的阶段标题
    assert "扫描" in p
    assert "提案" in p
    assert "确认" in p or "ask_user" in p
    assert "执行" in p
    # dry_run 默认 true 的纪律必须明文
    assert "dry_run" in p


def test_file_organizer_picked_up_by_registry_scan():
    reg = SkillRegistry()
    n = reg.scan(_BUILTINS)
    names = {m.name for m in reg.list()}
    assert "file_organizer" in names
    # document_convert 也在；总数 ≥ 2
    assert n >= 2
