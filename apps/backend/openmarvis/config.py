from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .browser.settings import BrowserSettings


class SecuritySettings(BaseModel):
    level: str = "normal"
    allow_sudo: bool = False
    allow_remote_script_exec: bool = False
    extra_path_blocklist: list[str] = Field(default_factory=list)


class LLMSettings(BaseModel):
    # 主对话/工具调用模型。LiteLLM 模型名 (provider/model)：
    #   openai/hunyuan-turbos-latest  — 腾讯混元（走 OpenAI 兼容端点，需配 api_base）
    #   deepseek/deepseek-chat        — DeepSeek V3，便宜、支持 function calling
    #   deepseek/deepseek-reasoner    — DeepSeek R1，推理强但更贵
    #   claude-opus-4-7 / sonnet-4-6  — Anthropic，质量好但贵
    provider_model: str = "openai/hunyuan-turbos-latest"
    # OpenAI 兼容端点的 base URL；非 OpenAI 兼容模型（deepseek/anthropic）留 None。
    # 混元: https://api.hunyuan.cloud.tencent.com/v1
    api_base: str | None = "https://api.hunyuan.cloud.tencent.com/v1"
    # 视觉/多模态模型 (analyze_image / vision_click / vision_type 使用)。
    # 主模型不支持视觉（DeepSeek/Hunyuan-turbos）时单独配一个：
    #   zhipu/glm-4v-flash            — 智谱，免费
    #   dashscope/qwen-vl-plus        — 阿里千问，极便宜
    #   claude-opus-4-7               — 回退到 Claude（贵）
    vision_model: str = "zhipu/glm-4v-flash"
    max_tokens: int = 4096
    temperature: float = 0.2


class WorkspaceSettings(BaseModel):
    root: Path = Path("~/.openmarvis").expanduser()
    max_total_gb: int = 20
    max_per_conv_mb: int = 2048
    warn_threshold_pct: int = 80


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENMARVIS_",
        env_nested_delimiter="__",
        extra="ignore",
        arbitrary_types_allowed=True,
    )
    host: str = "127.0.0.1"
    port: int = 8001
    cors_origins: list[str] = ["http://localhost:3000"]
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    workspace: WorkspaceSettings = Field(default_factory=WorkspaceSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    # 模型披露口径（Agent 被问及底层模型时的统一回答）。
    # 生产部署可改为实际模型组合描述，如 "腾讯混元 Hy3 + DeepSeek-V4 Pro"。
    model_disclosure: str = "OpenMarvis"
    # Runtime managers attached by app lifespan / build_main_agent — not loaded
    # from env. Declared here so pydantic's strict __setattr__ accepts them.
    scheduler_manager: Any = None
    skill_registry: Any = None


_settings: Settings | None = None


def get_settings(refresh: bool = False) -> Settings:
    global _settings
    if _settings is None or refresh:
        _settings = Settings()
    return _settings
