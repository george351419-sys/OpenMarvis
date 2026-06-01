from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseModel):
    level: str = "normal"
    allow_sudo: bool = False
    allow_remote_script_exec: bool = False
    extra_path_blocklist: list[str] = Field(default_factory=list)


class LLMSettings(BaseModel):
    provider_model: str = "claude-opus-4-7"
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
    )
    host: str = "127.0.0.1"
    port: int = 8001
    cors_origins: list[str] = ["http://localhost:3000"]
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    workspace: WorkspaceSettings = Field(default_factory=WorkspaceSettings)


_settings: Settings | None = None


def get_settings(refresh: bool = False) -> Settings:
    global _settings
    if _settings is None or refresh:
        _settings = Settings()
    return _settings
