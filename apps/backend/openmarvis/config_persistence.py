"""配置持久化模块：将运行时配置保存到 YAML 文件。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .config import Settings

DEFAULT_CONFIG_PATH = Path("~/.openmarvis/config.yaml").expanduser()


def load_config_from_yaml(path: Path | str | None = None) -> dict[str, Any]:
    """从 YAML 文件加载配置。

    返回的 dict 结构：
    {
        "llm": {"provider_model": "...", "temperature": 0.2, ...},
        "security": {"level": "normal", ...},
        "workspace": {"root": "...", ...},
    }
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data


def save_config_to_yaml(
    settings: Settings,
    path: Path | str | None = None,
    merge: bool = True,
) -> None:
    """将 Settings 对象保存到 YAML 文件。

    Args:
        settings: 要保存的配置对象
        path: 保存路径，默认 ~/.openmarvis/config.yaml
        merge: 是否与现有配置合并（保留未修改的字段）
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 准备要保存的数据
    data: dict[str, Any] = {}

    if merge and config_path.exists():
        # 加载现有配置
        data = load_config_from_yaml(config_path)

    # 更新配置（只保存可序列化的字段）
    data["llm"] = {
        "provider_model": settings.llm.provider_model,
        "api_base": settings.llm.api_base,
        "vision_model": settings.llm.vision_model,
        "max_tokens": settings.llm.max_tokens,
        "temperature": settings.llm.temperature,
    }

    data["security"] = {
        "level": settings.security.level,
        "allow_sudo": settings.security.allow_sudo,
        "allow_remote_script_exec": settings.security.allow_remote_script_exec,
        "extra_path_blocklist": settings.security.extra_path_blocklist,
    }

    data["workspace"] = {
        "root": str(settings.workspace.root),
        "max_total_gb": settings.workspace.max_total_gb,
        "max_per_conv_mb": settings.workspace.max_per_conv_mb,
        "warn_threshold_pct": settings.workspace.warn_threshold_pct,
    }

    # 保存到文件
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


def apply_yaml_config(settings: Settings, yaml_data: dict[str, Any]) -> None:
    """将 YAML 配置应用到 Settings 对象。

    直接修改传入的 settings 对象。
    """
    if "llm" in yaml_data:
        for key, value in yaml_data["llm"].items():
            if hasattr(settings.llm, key):
                setattr(settings.llm, key, value)

    if "security" in yaml_data:
        for key, value in yaml_data["security"].items():
            if hasattr(settings.security, key):
                setattr(settings.security, key, value)

    if "workspace" in yaml_data:
        for key, value in yaml_data["workspace"].items():
            if hasattr(settings.workspace, key):
                if key == "root":
                    settings.workspace.root = Path(value)
                else:
                    setattr(settings.workspace, key, value)


def get_config_path() -> Path:
    """获取配置文件路径（支持环境变量覆盖）。"""
    env_path = os.getenv("OPENMARVIS_CONFIG_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_CONFIG_PATH
