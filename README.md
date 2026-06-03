# OpenMarvis

> 开源 Marvis-like 桌面智能体 · macOS · Apache 2.0

OpenMarvis 是一款开源、可扩展的桌面 AI 助手框架，采用 Main Agent + Sub Agent 分层调度架构。

## 状态

- v0.5.0：+ Browser Agent + Computer Agent + Spotlight 工具
- v0.1.0：MVP 闭环（Main + File + Search Agent）
- 平台：macOS 14+
- 后端：Python 3.11 + FastAPI + Pydantic + LiteLLM + Playwright
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

### macOS 系统依赖（App Agent 用）

```bash
brew install cliclick     # Vision fallback 点击驱动
brew install pandoc       # document_convert skill 用
```

首次运行时，系统会请求 "Accessibility" 与 "Screen Recording" 权限：
"系统设置 → 隐私与安全性 → 辅助功能 / 屏幕录制" 中勾选 OpenMarvis（或运行它的终端 / Python）。

## 文档

- 架构 spec：`docs/superpowers/specs/2026-06-01-openmarvis-design.md`
- 实施计划：`docs/superpowers/plans/2026-06-01-openmarvis-m0-m1-mvp.md`
- 贡献指南：`CONTRIBUTING.md`

## v0.5.0 试一试

```
# 让 OpenMarvis 调你的音量
"调音量到 30%"

# 让 OpenMarvis 打开 GitHub 看你自己的仓库（首次需要登录）
"用 Browser Agent 打开 github.com 我的 dashboard 看一下我有几个 repo"

# 让 OpenMarvis 秒搜本地
"我桌面上最近有什么 .pdf？" 或 "找一下叫 invoice 的文件"

# 让 OpenMarvis 查电池剩余
"查一下当前电池剩余 / 电源状态"
```

## License

Apache 2.0 — 详见 LICENSE。
