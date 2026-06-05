"""Tests for settings API endpoints and utilities."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from openmarvis.api.settings import (
    _diagnose_workspace,
    _key_presence,
    _validate_key_format,
)


class TestKeyValidation:
    """测试 API key 格式验证。"""

    def test_valid_anthropic_key(self):
        result = _validate_key_format("sk-ant-api03-abcd1234567890", "anthropic/")
        assert result["valid"] is True

    def test_invalid_anthropic_key_prefix(self):
        result = _validate_key_format("invalid-key-1234567890", "anthropic/")
        assert result["valid"] is False
        assert result["reason"] == "invalid_prefix"
        assert result["expected"] == "sk-ant-*"

    def test_valid_openai_key(self):
        result = _validate_key_format("sk-abcdef1234567890", "openai/")
        assert result["valid"] is True

    def test_invalid_openai_key_prefix(self):
        result = _validate_key_format("invalid-1234567890", "openai/")
        assert result["valid"] is False
        assert result["reason"] == "invalid_prefix"

    def test_too_short_key(self):
        result = _validate_key_format("sk-123", "openai/")
        assert result["valid"] is False
        assert result["reason"] == "too_short"

    def test_empty_key(self):
        result = _validate_key_format("", "openai/")
        assert result["valid"] is False
        assert result["reason"] == "empty"

    def test_whitespace_key(self):
        result = _validate_key_format("   ", "openai/")
        assert result["valid"] is False
        assert result["reason"] == "empty"


class TestKeyPresence:
    """测试 API key 存在性探测。"""

    def test_unknown_provider(self):
        result = _key_presence("unknown-provider/model")
        assert result["any_present"] is None
        assert result["hint"] == "unknown provider prefix"

    def test_anthropic_key_present(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-12345678901234567890"}):
            result = _key_presence("anthropic/claude-3-opus")
            assert result["any_present"] is True
            assert result["present_env"] == "ANTHROPIC_API_KEY"
            assert "validation" in result
            assert result["validation"]["valid"] is True
            assert "key_prefix" in result
            assert result["key_prefix"].startswith("sk-ant-t")

    def test_anthropic_key_absent(self):
        with patch.dict(os.environ, {}, clear=False):
            # 确保环境变量不存在
            os.environ.pop("ANTHROPIC_API_KEY", None)
            result = _key_presence("anthropic/claude-3-opus")
            assert result["any_present"] is False
            assert result["present_env"] is None
            assert "validation" not in result

    def test_openai_fallback_to_hunyuan(self):
        with patch.dict(os.environ, {"HUNYUAN_API_KEY": "test-key-1234567890"}):
            result = _key_presence("openai/gpt-4")
            assert result["any_present"] is True
            assert result["present_env"] == "HUNYUAN_API_KEY"
            assert "HUNYUAN_API_KEY" in result["checked_envs"]
            assert "OPENAI_API_KEY" in result["checked_envs"]

    def test_deepseek_key_validation(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test1234567890"}):
            result = _key_presence("deepseek/deepseek-chat")
            assert result["any_present"] is True
            assert result["validation"]["valid"] is True


class TestWorkspaceDiagnosis:
    """测试 workspace 目录诊断。"""

    def test_existing_directory(self, tmp_path):
        result = _diagnose_workspace(tmp_path)
        assert result["exists"] is True
        assert result["readable"] is True
        assert result["writable"] is True
        assert "disk" in result
        assert result["disk"]["total_gb"] > 0
        assert "current_size_mb" in result

    def test_nonexistent_directory(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        result = _diagnose_workspace(nonexistent)
        assert result["exists"] is False
        assert result["parent_exists"] is True
        assert result["can_create"] is True

    def test_deeply_nested_nonexistent(self, tmp_path):
        deep_path = tmp_path / "level1" / "level2" / "level3" / "workspace"
        result = _diagnose_workspace(deep_path)
        assert result["exists"] is False
        # 父目录也不存在
        assert result["parent_exists"] is False
        assert result["can_create"] is False
