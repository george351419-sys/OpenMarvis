# OpenMarvis

> 开源 Marvis-like 桌面智能体 · macOS · Apache 2.0

OpenMarvis 是一款开源、可扩展的桌面 AI 助手框架，采用 Main Agent + Sub Agent 分层调度架构。

## 状态

- v0.1.0：MVP 闭环（Main + File + Search Agent），macOS 14+
- 后端：Python 3.11 + FastAPI + Pydantic + LiteLLM
- 前端：Next.js 14 + Tailwind + shadcn/ui

## 快速开始

前置：Python 3.11、Node 20、pnpm 9。

```bash
git clone <repo> openmarvis && cd openmarvis
make install
export ANTHROPIC_API_KEY=...
make dev
```

打开 http://localhost:3000。

## 文档

- 架构 spec：`docs/superpowers/specs/2026-06-01-openmarvis-design.md`
- 实施计划：`docs/superpowers/plans/2026-06-01-openmarvis-m0-m1-mvp.md`
- 贡献指南：`CONTRIBUTING.md`

## License

Apache 2.0 — 详见 LICENSE。
