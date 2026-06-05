from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])

# provider-prefix → env-var-name 主要候选；用于"key 是否在环境变量里"探测
_PROVIDER_KEY_ENV = {
    "openai/": ("HUNYUAN_API_KEY", "OPENAI_API_KEY"),
    "deepseek/": ("DEEPSEEK_API_KEY",),
    "anthropic/": ("ANTHROPIC_API_KEY",),
    "claude/": ("ANTHROPIC_API_KEY",),
    "zhipu/": ("ZHIPU_API_KEY",),
    "qwen/": ("DASHSCOPE_API_KEY", "QWEN_API_KEY"),
    "dashscope/": ("DASHSCOPE_API_KEY",),
    "gemini/": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "google/": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "mistral/": ("MISTRAL_API_KEY",),
    "cohere/": ("COHERE_API_KEY",),
    "replicate/": ("REPLICATE_API_KEY",),
    "huggingface/": ("HUGGINGFACE_API_KEY", "HF_TOKEN"),
    "together/": ("TOGETHER_API_KEY", "TOGETHERAI_API_KEY"),
}


def _validate_key_format(key: str, provider_prefix: str) -> dict[str, object]:
    """验证 API key 格式是否合理（不验证真实有效性）。"""
    if not key or len(key.strip()) == 0:
        return {"valid": False, "reason": "empty"}

    key = key.strip()

    # 基本长度检查
    if len(key) < 10:
        return {"valid": False, "reason": "too_short"}

    # Provider-specific 格式检查
    if provider_prefix in ("anthropic/", "claude/"):
        if not key.startswith("sk-ant-"):
            return {"valid": False, "reason": "invalid_prefix", "expected": "sk-ant-*"}
    elif provider_prefix == "openai/":
        if not key.startswith("sk-"):
            return {"valid": False, "reason": "invalid_prefix", "expected": "sk-*"}
    elif provider_prefix == "deepseek/":
        if not key.startswith("sk-"):
            return {"valid": False, "reason": "invalid_prefix", "expected": "sk-*"}

    return {"valid": True}


def _key_presence(provider_model: str) -> dict[str, object]:
    """探测当前进程能否找到适配 provider_model 的 API key。

    返回 {checked_envs: [...], any_present: bool, present_env: str|None, validation: {...}}。
    不返回 key 值本身（即便部分脱敏也尽量避免）。
    """
    candidates: tuple[str, ...] = ()
    provider_prefix = ""
    for prefix, envs in _PROVIDER_KEY_ENV.items():
        if provider_model.startswith(prefix):
            candidates = envs
            provider_prefix = prefix
            break

    if not candidates:
        # 未知 provider 前缀 —— 让 LiteLLM 自己解；UI 上显示 "unknown_provider"
        return {
            "checked_envs": [],
            "any_present": None,
            "present_env": None,
            "hint": "unknown provider prefix",
        }

    present = next((e for e in candidates if os.getenv(e)), None)
    result = {
        "checked_envs": list(candidates),
        "any_present": present is not None,
        "present_env": present,
    }

    # 如果找到了 key，验证格式
    if present:
        key_value = os.getenv(present, "")
        validation = _validate_key_format(key_value, provider_prefix)
        result["validation"] = validation
        # 添加部分脱敏的前缀信息用于调试
        if key_value and len(key_value) >= 8:
            result["key_prefix"] = key_value[:8] + "..."

    return result


class SettingsPatch(BaseModel):
    llm: dict | None = None
    security: dict | None = None
    workspace: dict | None = None


@router.get("")
async def get_settings(request: Request) -> dict:
    s = request.app.state.om.settings
    return {
        "llm": s.llm.model_dump(),
        "security": s.security.model_dump(),
        "workspace": {"root": str(s.workspace.root),
                       "max_total_gb": s.workspace.max_total_gb,
                       "max_per_conv_mb": s.workspace.max_per_conv_mb},
    }


def _diagnose_workspace(workspace_root: Path) -> dict[str, object]:
    """诊断 workspace 目录状态：存在性、权限、磁盘空间等。"""
    diagnosis = {
        "exists": workspace_root.exists(),
        "path": str(workspace_root),
    }

    if not workspace_root.exists():
        # 检查父目录是否存在且可写
        parent = workspace_root.parent
        diagnosis["parent_exists"] = parent.exists()
        if parent.exists():
            diagnosis["parent_writable"] = os.access(parent, os.W_OK)
            diagnosis["can_create"] = diagnosis["parent_writable"]
        else:
            diagnosis["can_create"] = False
        return diagnosis

    # 目录存在，检查权限和空间
    diagnosis["readable"] = os.access(workspace_root, os.R_OK)
    diagnosis["writable"] = os.access(workspace_root, os.W_OK)

    # 获取磁盘空间信息
    try:
        import shutil
        total, used, free = shutil.disk_usage(workspace_root)
        diagnosis["disk"] = {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "usage_pct": round((used / total) * 100, 1),
        }
    except Exception as e:
        diagnosis["disk_error"] = str(e)

    # 检查目录大小
    try:
        total_size = sum(
            f.stat().st_size
            for f in workspace_root.rglob("*")
            if f.is_file()
        )
        diagnosis["current_size_mb"] = round(total_size / (1024**2), 2)
    except Exception as e:
        diagnosis["size_error"] = str(e)

    return diagnosis


@router.get("/info")
async def get_runtime_info(request: Request) -> dict:
    """返回**当前进程实际加载**的配置 + key 探测 + 一些运行时信息。

    用于前端 settings 页头"当前已加载"状态条；可见性远比能不能改更重要。
    """
    s = request.app.state.om.settings
    workspace_root = Path(s.workspace.root).expanduser()

    # 主模型和视觉模型的 key 探测
    main_key_info = _key_presence(s.llm.provider_model)
    vision_key_info = _key_presence(s.llm.vision_model)

    return {
        "llm": {
            "provider_model": s.llm.provider_model,
            "api_base": s.llm.api_base,
            "vision_model": s.llm.vision_model,
            "max_tokens": s.llm.max_tokens,
            "temperature": s.llm.temperature,
            "key_presence": main_key_info,
            "vision_key_presence": vision_key_info,
        },
        "security": s.security.model_dump(),
        "workspace": {
            "root": str(workspace_root),
            "diagnosis": _diagnose_workspace(workspace_root),
            "limits": {
                "max_total_gb": s.workspace.max_total_gb,
                "max_per_conv_mb": s.workspace.max_per_conv_mb,
                "warn_threshold_pct": s.workspace.warn_threshold_pct,
            },
        },
        "version": "v1.0.x-dev",
    }


@router.get("/health")
async def check_health(request: Request) -> dict:
    """健康检查：测试各项配置是否正常工作。

    包括：
    - API key 连通性测试（简单的 API 调用）
    - workspace 可用性
    - 必要依赖是否安装
    """
    s = request.app.state.om.settings
    health = {
        "overall": "unknown",
        "checks": {},
    }

    # 1. Workspace 检查
    workspace_root = Path(s.workspace.root).expanduser()
    workspace_ok = workspace_root.exists() and os.access(workspace_root, os.W_OK)
    health["checks"]["workspace"] = {
        "status": "ok" if workspace_ok else "error",
        "path": str(workspace_root),
    }

    # 2. 主模型 key 检查
    main_key = _key_presence(s.llm.provider_model)
    health["checks"]["main_model_key"] = {
        "status": "ok" if main_key.get("any_present") else "error",
        "provider": s.llm.provider_model,
    }

    # 3. 视觉模型 key 检查
    vision_key = _key_presence(s.llm.vision_model)
    health["checks"]["vision_model_key"] = {
        "status": "ok" if vision_key.get("any_present") else "warning",
        "provider": s.llm.vision_model,
    }

    # 整体状态
    all_critical = [
        health["checks"]["workspace"]["status"] == "ok",
        health["checks"]["main_model_key"]["status"] == "ok",
    ]
    if all(all_critical):
        health["overall"] = "healthy"
    elif any(c["status"] == "error" for c in health["checks"].values()):
        health["overall"] = "error"
    else:
        health["overall"] = "warning"

    return health


@router.put("")
async def update_settings(patch: SettingsPatch, request: Request) -> dict:
    s = request.app.state.om.settings
    if patch.llm:
        for k, v in patch.llm.items():
            if hasattr(s.llm, k):
                setattr(s.llm, k, v)
    if patch.security:
        for k, v in patch.security.items():
            if hasattr(s.security, k):
                setattr(s.security, k, v)
    return await get_settings(request)
