from __future__ import annotations

import pytest

from openmarvis.skill.manifest import SkillLoadError, load_skill
from openmarvis.skill.registry import SkillRegistry


def _write_skill(root, name, yaml_body, prompt="prompt body"):
    d = root / name
    d.mkdir(parents=True)
    (d / "skill.yaml").write_text(yaml_body, encoding="utf-8")
    if prompt is not None:
        (d / "prompt.md").write_text(prompt, encoding="utf-8")
    return d


def test_load_skill_happy_path(tmp_path):
    d = _write_skill(tmp_path, "doc",
        "name: doc\nversion: 1.0.0\ndescription: x\n"
        "params:\n"
        "  source: {type: string, required: true}\n"
        "  fmt: {type: string, enum: [md, pdf]}\n"
        "allowed_tools: [fs.read_file, exec.shell]\n"
        "risk: medium\n",
        prompt="hello {{source}}",
    )
    m = load_skill(d)
    assert m.name == "doc"
    assert m.risk == "medium"
    assert m.allowed_tools == ["fs.read_file", "exec.shell"]
    assert m.params["source"].required is True
    assert m.params["fmt"].enum == ["md", "pdf"]
    assert m.prompt == "hello {{source}}"
    assert m.root == d


def test_load_skill_missing_yaml(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    with pytest.raises(SkillLoadError):
        load_skill(d)


def test_load_skill_invalid_yaml(tmp_path):
    d = _write_skill(tmp_path, "bad", "::: not yaml", prompt=None)
    with pytest.raises(SkillLoadError):
        load_skill(d)


def test_validate_params_fills_defaults_and_rejects_unknown(tmp_path):
    d = _write_skill(tmp_path, "x",
        "name: x\n"
        "params:\n"
        "  a: {type: string, required: true}\n"
        "  b: {type: string, default: hello}\n",
    )
    m = load_skill(d)
    assert m.validate_params({"a": "v"}) == {"a": "v", "b": "hello"}
    with pytest.raises(ValueError, match="missing required"):
        m.validate_params({"b": "y"})
    with pytest.raises(ValueError, match="unknown params"):
        m.validate_params({"a": "v", "c": "?"})


def test_validate_params_enum(tmp_path):
    d = _write_skill(tmp_path, "x",
        "name: x\n"
        "params:\n"
        "  fmt: {type: string, enum: [md, pdf]}\n",
    )
    m = load_skill(d)
    assert m.validate_params({"fmt": "md"}) == {"fmt": "md"}
    with pytest.raises(ValueError, match="must be one of"):
        m.validate_params({"fmt": "docx"})


def test_registry_scans_and_skips_invalid(tmp_path):
    _write_skill(tmp_path, "good", "name: good\n")
    _write_skill(tmp_path, "broken", "::: not yaml", prompt=None)
    _write_skill(tmp_path, "two", "name: two\n")
    # Empty dir without skill.yaml — should be ignored silently
    (tmp_path / "empty_dir").mkdir()

    reg = SkillRegistry()
    count = reg.scan(tmp_path)
    assert count == 2
    assert {m.name for m in reg.list()} == {"good", "two"}
    assert reg.get("good").name == "good"
    assert reg.get("missing") is None


def test_registry_scan_nonexistent_root(tmp_path):
    reg = SkillRegistry()
    assert reg.scan(tmp_path / "does-not-exist") == 0
