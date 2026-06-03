# OpenMarvis

> 开源 Marvis-like 桌面智能体 · macOS · Apache 2.0

OpenMarvis 是一款开源、可扩展的桌面 AI 助手框架，采用 Main Agent + Sub Agent 分层调度架构。

## 状态

- v1.0.0：+ App Agent（macOS UI 自动化）+ Skill 体系 + Scheduler（定时任务）+ Timeline 面板
- v0.5.0：+ Browser Agent + Computer Agent + Spotlight 工具
- v0.1.0：MVP 闭环（Main + File + Search Agent）
- 平台：macOS 14+
- 5 个 Sub Agent：file / search / browser / computer / app
- 后端：Python 3.11 + FastAPI + Pydantic + LiteLLM + Playwright + APScheduler
- 前端：Next.js 14 + Tailwind + shadcn/ui + zustand

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
- 测试指南：[`docs/TESTING.md`](docs/TESTING.md)
- 贡献指南：`CONTRIBUTING.md`

## v1.0.0 试一试

```
# App Agent：操作 macOS 应用 UI
"在 Notes 里建一条标题为「明天会议」的笔记"

# Skill：固定工作流
"用 document_convert 把 ~/Desktop/notes.md 转成 pdf"

# Scheduler：定时任务
"每天早上 9 点给我发一条北京今天的天气"
# → 侧边栏 🕒 看任务，🔔 看结果

# v0.5 能力同样可用
"调音量到 30%"
"用 Browser Agent 看一下我的 GitHub dashboard"
"我桌面上最近有什么 .pdf？"
```

侧边栏入口：
- ✨ Skills — 已安装 skill 清单
- 🕒 定时任务 — 列出 / 取消
- 🔔 通知 — 定时任务执行结果

右栏 Timeline 实时显示 agent / tool-call 轨迹。

## License

Apache 2.0 — 详见 LICENSE。
