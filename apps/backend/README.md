# OpenMarvis Backend

FastAPI 后端服务，提供 /chat SSE、/conversations、/files、/settings 等 API。

## 开发

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn openmarvis.main:app --reload --port 8001
```

## 测试

```bash
.venv/bin/pytest -v                       # 不跑覆盖率，快
.venv/bin/pytest --cov                    # 跑覆盖率；< 85% 视为失败
```

覆盖率门槛 85%（`[tool.coverage.report].fail_under`）。本地新增代码后用 `--cov` 跑一遍确认没拉低总体。

## 配置

环境变量前缀 `OPENMARVIS_`，嵌套用 `__` 分隔，例如：
- `OPENMARVIS_LLM__PROVIDER_MODEL=claude-opus-4-7`
- `OPENMARVIS_SECURITY__LEVEL=strict`
- `ANTHROPIC_API_KEY=...`（LiteLLM 透传）
- `BRAVE_SEARCH_API_KEY=...`（web_search 用，可选）
