# OpenMarvis Testing Guide

> 适用范围：v1.0.0 之后所有提交 / Release。
> 受众：贡献者、release 负责人、CI 维护者。

OpenMarvis 的目标是**让每次提交都跑得起、跑得快、跑得准**：本地 8 秒内拿到信号，CI 全套 < 1 分钟（含 e2e 非 live 部分），需要真实 LLM / 真实 macOS 权限的场景显式 opt-in 放进 live 通道。

文档结构：

1. [测试金字塔与命名约定](#1-测试金字塔与命名约定)
2. [跑测试 — 速查表](#2-跑测试--速查表)
3. [后端 pytest 套件](#3-后端-pytest-套件)
4. [前端 typecheck + 单元](#4-前端-typecheck--单元)
5. [Playwright e2e](#5-playwright-e2e)
6. [Live 通道：真实 LLM / 真实权限](#6-live-通道真实-llm--真实权限)
7. [覆盖率门槛 85%](#7-覆盖率门槛-85)
8. [Fixtures 与隔离原则](#8-fixtures-与隔离原则)
9. [写新测试 — 决策表](#9-写新测试--决策表)
10. [Release 前的 checklist](#10-release-前的-checklist)

---

## 1. 测试金字塔与命名约定

```
                       ┌────────────────────┐
                       │  e2e live (手动)    │  4 specs，跑真 LLM + 真 macOS UI
                       ├────────────────────┤
                       │  e2e offline (CI)   │  3 specs，纯前端冒烟
                       ├────────────────────┤
                       │  API endpoint 测试  │  ~30 cases，TestClient 走全栈
                       ├────────────────────┤
                       │  unit + 单元 mock   │  ~200 cases，msg/解析/守门
                       └────────────────────┘
```

**目录约定**：

| 路径 | 跑什么 | 触发 |
|---|---|---|
| `apps/backend/tests/<area>/test_*.py` | 按 area 切分（`scheduler/` / `skill/` / `app_automation/` / `browser/` / `computer/`）的单元 + API 测试 | `pytest` |
| `apps/backend/tests/test_*.py` | 顶层 cross-cutting（agent_loop / chat_sse / security_*）| `pytest` |
| `apps/backend/tests/integration/test_*_live.py` | 真实 LLM / 真实浏览器 / Spotlight | `OPENMARVIS_LIVE=1 pytest` |
| `apps/web/tests/e2e/*.spec.ts` | Playwright 全链路 | `pnpm exec playwright test` |
| `apps/web/tests/e2e/*-live.spec.ts` 或带 `test.skip(!process.env.OPENMARVIS_E2E_LIVE, …)` | 跑真 LLM 的 e2e | `OPENMARVIS_LIVE=1 pnpm exec playwright test` |

**文件命名**：

- 后端：测哪个模块就是 `test_<modname>.py`；API 测试一律 `test_<resource>_api.py`。
- 前端 e2e：`<feature>.spec.ts`；要 live 的加 `-live` 后缀（如 `schedule-create-live.spec.ts`）。

---

## 2. 跑测试 — 速查表

> 多条命令请逐条执行。

后端日常（不算覆盖率，快）：

```bash
cd apps/backend
.venv/bin/pytest -v
```

后端发版前（含覆盖率门槛）：

```bash
cd apps/backend
.venv/bin/pytest --cov
```

前端日常：

```bash
cd apps/web
npm run typecheck
```

前端 e2e（CI / 非 live，3 specs）：

```bash
cd apps/web
pnpm exec playwright test schedules-page skills-page timeline-and-bell
```

前端 e2e（live，会真的跟 Anthropic API 通信）：

```bash
cd apps/web
export ANTHROPIC_API_KEY=sk-ant-...
export OPENMARVIS_LIVE=1
pnpm exec playwright test
```

后端 live（真浏览器 / Spotlight / Computer Agent）：

```bash
cd apps/backend
export ANTHROPIC_API_KEY=sk-ant-...
export OPENMARVIS_LIVE=1
.venv/bin/pytest tests/integration/ -v
```

---

## 3. 后端 pytest 套件

**当前规模**：232 cases，3 skipped（live 默认跳过），跑全套 < 10 秒。

**按 area 一览**：

| Area | 主要文件 | 覆盖什么 |
|---|---|---|
| **agent 核心** | `test_agent_loop.py` / `test_main_agent.py` | LLM 工具循环、message_history、iteration_limit、ReAct 分支 |
| **chat SSE** | `test_chat_sse.py` / `test_echo_sse.py` / `test_chat_scheduled_path.py` | EventSourceResponse、scheduled trigger 路径、filter_registry |
| **API 端点** | `test_api_conversations.py` / `test_api_files.py` / `test_api_settings.py` / `test_healthz.py` / `test_notifications_api.py` / `test_schedules_api.py` / `test_skills_api.py` | 走 TestClient，含 404 / 400 / 空态 |
| **安全** | `test_security_*.py` / `test_security_gate*.py` | PathGuard / CmdGuard / CredentialGuard、`assess_risk()` 升级链 |
| **存储** | `test_store_*.py` / `test_memory_store.py` / `test_workspace.py` / `test_sub_agents_store.py` | SQLModel 表 + 业务 helper |
| **工具** | `test_tools_*.py` | 每个 Tool 各自的参数校验、风险、执行 |
| **scheduler** | `tests/scheduler/test_*.py` | manager / tools_schedule / trigger_filter / trigger_runner / rehydrate |
| **skill** | `tests/skill/test_*.py` | manifest 解析 / registry 扫描 / runner / UseSkillTool |
| **app_automation** | `tests/app_automation/test_*.py` | node_ref 编解码、AXBackend、Vision、cliclick wrapper、permission probe |
| **browser** | `tests/browser/test_*.py` | BrowserPool、11 个 tool、settings |
| **computer** | `tests/computer/test_*.py` | 19 个 macOS 工具的 mock 验证 |

**Mark 与跳过**：

- 默认禁用：`integration/` 通过 `tests/integration/conftest.py` 在 `OPENMARVIS_LIVE` 与 `OPENMARVIS_M2_LIVE` 都不为 `"1"` 时整体跳过。
- 异步 mode：`pyproject.toml` 设 `asyncio_mode = "auto"`，写 `@pytest.mark.asyncio` 不是必须的，但保留对老代码兼容。

---

## 4. 前端 typecheck + 单元

**typecheck** 是发版前最低门槛：

```bash
cd apps/web && npm run typecheck   # tsc --noEmit
```

**纯 React 单元** 暂未引入 jest / vitest（M3-E plan 里 D6 / E2 列了 jest，但 v1.0 尚未实装，因为 ChatStream / TimelinePanel 等组件已被 e2e 实际驱动覆盖）。原则：

- 纯计算函数（如 `lib/stores/timeline.ts` 的 `ingest` reducer）— 后续要加单元测试，建议 vitest（跟 Next.js / TS 配合最少胶水）。
- 视图组件 — 用 Playwright 真渲染，比 React Testing Library 更接近用户。

---

## 5. Playwright e2e

**配置**：`apps/web/playwright.config.ts`

- baseURL `http://localhost:3000`
- `webServer` 同时启 backend (`uvicorn :8001`) + frontend (`pnpm dev :3000`)，`reuseExistingServer: true`，意味着本地已经起着就不重复启
- `headless: true`，`trace: retain-on-failure`

**现有 specs（共 7 个，3 个 CI 可跑 / 4 个 live）**：

| Spec | Live? | 覆盖什么 |
|---|---|---|
| `schedules-page.spec.ts` | ❌ CI 可跑 | `/schedules` 空态文案 + 刷新 + 返回 |
| `skills-page.spec.ts` | ❌ CI 可跑 | `/skills` 展示内置 `document_convert` + 参数展开 |
| `timeline-and-bell.spec.ts` | ❌ CI 可跑 | 会话页右栏 Timeline + 顶栏 toggle + 侧栏铃铛 |
| `browser-agent-extract.spec.ts` | ✅ live | 真 LLM 调 browser-agent 抓页面内容 |
| `computer-volume.spec.ts` | ✅ live | 真 LLM 调 computer-agent 读音量 |
| `desktop-write-confirm.spec.ts` | ✅ live | 真 LLM 触发 medium-risk confirm 流 |
| `pdf-summary.spec.ts` | ✅ live | 真 LLM + file-agent 处理 fixture PDF |
| `search-compare.spec.ts` | ✅ live | 真 LLM + search-agent 联网 |
| `schedule-create-live.spec.ts` | ✅ live | 真 LLM 调 create_schedule，过 confirm，验 `/schedules` 出现 |

**Fixtures**：`apps/web/tests/e2e/fixtures/hello.pdf` —— 仅有的二进制 fixture。

**关键 gotcha**：

- webServer 冷启动慢 → 关键 `toBeVisible` 加 `timeout: 15_000`，不要默认 5s。
- 多个 spec 并行跑时共享同一个 backend 进程；测 `/schedules` 等 stateful 端点要么各自隔离 conv_id，要么用 `fullyParallel: false`（当前配置）。

---

## 6. Live 通道：真实 LLM / 真实权限

**统一环境变量**（v1.0 起）：`OPENMARVIS_LIVE=1` 同时开启前端 e2e + 后端 integration 的 live 通道。仍可用旧变量 `OPENMARVIS_M2_LIVE=1`（后端）和 `OPENMARVIS_E2E_LIVE=1`（前端）作为 deprecated alias，便于增量迁移。

| 变量 | 作用域 | 还需要什么 |
|---|---|---|
| `OPENMARVIS_LIVE=1` 🆕 | 前端 e2e + 后端 integration 全部 | `ANTHROPIC_API_KEY`、Playwright Chromium、macOS 权限 |
| `OPENMARVIS_M2_LIVE=1`（alias）| 仅后端 integration | 同上 |
| `OPENMARVIS_E2E_LIVE=1`（alias）| 仅前端 e2e | 同上 |

**安全提醒**：

- `desktop-write-confirm.spec.ts` 真的写文件；fixture 限定在 workspace `output/` 下。
- `computer-volume.spec.ts` 真的调系统音量；跑完会恢复（但中途异常退出可能留 30%）。
- 不要在 CI 跑 live。GitHub Actions runner 既没有 GUI，也不应该花 Anthropic 配额。

**推荐什么时候跑**：

- 发版前一天本地跑一遍全套 live，发现 prompt 回归。
- 改了 SubAgent prompt → 跑对应那个 agent 的 live spec。
- 改了 SecurityGate → 至少跑 `desktop-write-confirm`。

---

## 7. 覆盖率门槛 85%

配置在 `apps/backend/pyproject.toml`：

```toml
[tool.coverage.run]
source = ["openmarvis"]
omit = ["openmarvis/skill/builtins/*"]

[tool.coverage.report]
fail_under = 85
show_missing = true
exclude_also = [
  "pragma: no cover",
  "if TYPE_CHECKING:",
  "raise NotImplementedError",
]
```

**当前总覆盖率**：85.79%（v1.0.0 发布时）。

**如何低于门槛**：`pytest --cov` 会以 `fail` 退出，CI 红。补救路径优先级：

1. 是不是新加的某个文件没跟测试一起进？给它写测试。
2. 是不是一个 mock-heavy 模块本来就不该测（如 `openmarvis/app_automation/ax_backend.py` 51% 是因为大量代码只在真实 AX 树存在时跑）？加进 `omit` 而不是放低门槛。
3. 加一行 `# pragma: no cover` 只能用在**确实不可达**的分支上（如 NotImplementedError 派生类的默认 stub）。

**不上调门槛的理由**：

- App Agent / browser 工具大量依赖 macOS / Playwright 真实环境，单元 mock 不会变多。
- 强行追到 90% 容易拿 `from x import Y` 这种 line 凑数，对实际信号没贡献。

---

## 8. Fixtures 与隔离原则

**`apps/backend/tests/conftest.py`** —— 关键 fixture：

```python
@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("OPENMARVIS_WORKSPACE__ROOT", str(tmp_path / "om"))
    with TestClient(create_app()) as c:
        yield c
```

每个测试拿到独立 `tmp_path/om/data.db`，含独立 ScheduleManager / SkillRegistry。**绝对不要**让两个测试共享 `~/.openmarvis/data.db` —— v1.0 开发期被这条坑过：rehydrate 把上一个 case 的 schedule 拉进下一个 case，断言全错。

**Mock 原则**：

- LLM 调用：Mock `LiteLLMClient.stream_chat` 返回固定 chunks；不要 mock 到 HTTP 层。
- macOS API（pyobjc / Quartz）：测试不强求装 pyobjc，permission_probe 类的代码自带 `ImportError` fallback。
- 浏览器（Playwright）：测试不真起 Chromium，BrowserPool 用 MagicMock 替换 page 对象。
- APScheduler：用真的 `AsyncIOScheduler` + `MemoryJobStore`，跑得起就跑（trigger 时间设到 1 年后避免误触发）。

---

## 9. 写新测试 — 决策表

收到一个新 PR 要测什么？按这张表：

| 改动类型 | 必须有的测试 | 视情况补的 |
|---|---|---|
| 新工具（`Tool` 派生类） | `test_tools_<name>.py`：参数校验、风险、execute happy path | 单元 mock 一个失败路径 |
| 新 API 端点 | `test_<resource>_api.py`：200 / 404 / 422 三个 status | 边界值（空字符串、超长） |
| 新 Sub Agent | `test_dispatch_<name>.py`：dispatch_task 路由 + 一个 mock 执行链 | live e2e |
| 新 Skill | manifest validate_params 测试 + `/skills` 端点能看到 | golden tests 放 skill 自己的 `tests/` |
| 新 SSE 事件 | `test_chat_sse.py` 加一个 assert | 前端 `useTimeline` 的 reducer 测试 |
| 改 SecurityGate / 守门 | `test_security_*.py` 加场景：被拦的 + 被放行的 | live confirm flow |
| 改 prompt | 至少手测一遍 + 触发对应 live spec | 不必加单元测试 |
| 改前端组件视觉 | typecheck + 至少 1 个 Playwright 截图 spec | （没单元测试框架，e2e 兜底）|

---

## 10. Release 前的 checklist

```
[ ] cd apps/backend && .venv/bin/pytest --cov       # 含 85% 门槛
[ ] cd apps/web && npm run typecheck
[ ] cd apps/web && pnpm exec playwright test schedules-page skills-page timeline-and-bell
[ ] （可选）OPENMARVIS_LIVE=1 .venv/bin/pytest tests/integration/
[ ] （可选）OPENMARVIS_E2E_LIVE=1 pnpm exec playwright test
[ ] CHANGELOG.md 加新版本段落
[ ] .release-notes-v<X.Y.Z>.md 生成（可从 CHANGELOG 抠）
[ ] git tag -a v<X.Y.Z> -F .release-notes-v<X.Y.Z>.md
[ ] git push origin main && git push origin v<X.Y.Z>
[ ] # tag 推送会触发 .github/workflows/release.yml 自动建 draft release；
    # 直接去 GitHub 上 Publish 即可。也可手动跑 gh release create --draft。
```

一行版本：

```bash
cd apps/backend && .venv/bin/pytest --cov && \
cd ../web && npm run typecheck && \
pnpm exec playwright test schedules-page skills-page timeline-and-bell
```
