# Contributing to OpenMarvis

欢迎贡献！

## 工作流

1. Fork + clone
2. `make install`
3. 在新分支开发
4. `make test && make typecheck && make lint`
5. PR 描述含：动机 / 改动点 / 测试范围

## 工具

- 后端测试：`.venv/bin/pytest`
- 前端检查：`pnpm typecheck:web && pnpm lint:web`
- 端到端：`pnpm e2e`（需 ANTHROPIC_API_KEY）

## 准则

- 优先小步提交（一个原子改动 = 一个 commit）
- 新加工具/Sub Agent 必须配单测 + 安全等级声明
- 文档与 spec 一同更新
