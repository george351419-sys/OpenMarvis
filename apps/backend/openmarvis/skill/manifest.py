from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError


class SkillParam(BaseModel):
    type: str = Field(description="json-schema-style: string / integer / number / boolean / array / object")
    description: str = ""
    required: bool = False
    enum: list[str] | None = None
    default: Any = None


class SkillManifest(BaseModel):
    name: str
    version: str = "0.0.1"
    description: str = ""
    author: str = ""
    license: str = ""
    risk: str = "low"                                   # low / medium / high
    params: dict[str, SkillParam] = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    requires_python_packages: list[str] = Field(default_factory=list)

    # Populated after load:
    root: Path | None = None
    prompt: str = ""

    def validate_params(self, supplied: dict[str, Any]) -> dict[str, Any]:
        """Return supplied filled with defaults; raise ValueError on missing/typo."""
        out: dict[str, Any] = {}
        for name, spec in self.params.items():
            if name in supplied:
                v = supplied[name]
                if spec.enum is not None and v not in spec.enum:
                    raise ValueError(
                        f"param '{name}' must be one of {spec.enum}, got {v!r}")
                out[name] = v
            elif spec.default is not None:
                out[name] = spec.default
            elif spec.required:
                raise ValueError(f"missing required param: {name}")
        unknown = set(supplied) - set(self.params)
        if unknown:
            raise ValueError(f"unknown params: {sorted(unknown)}")
        return out


class SkillLoadError(ValueError):
    pass


def load_skill(skill_dir: Path) -> SkillManifest:
    """Parse `{skill_dir}/skill.yaml` and load adjacent prompt.md."""
    yaml_path = skill_dir / "skill.yaml"
    prompt_path = skill_dir / "prompt.md"
    if not yaml_path.is_file():
        raise SkillLoadError(f"skill.yaml not found in {skill_dir}")
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise SkillLoadError(f"invalid skill.yaml in {skill_dir}: {e}") from e
    try:
        manifest = SkillManifest(**data)
    except ValidationError as e:
        raise SkillLoadError(f"invalid skill manifest in {skill_dir}: {e}") from e
    manifest.root = skill_dir
    if prompt_path.is_file():
        manifest.prompt = prompt_path.read_text(encoding="utf-8")
    return manifest
