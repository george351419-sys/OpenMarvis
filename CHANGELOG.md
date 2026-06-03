# Changelog

## Unreleased — v1.0.0

OpenMarvis M3 整体落地：App Agent / Skill / Scheduler / Timeline 四块拼图同时上线，第 5 个 Sub Agent + 60 余个工具，macOS 全栈桌面 AI 助手能力闭环。

### Added — App Agent（M3-A）

- **App Agent** — 第 5 个 Sub Agent，专门操作 macOS GUI 应用；通过 `dispatch_task("app-agent", ...)` 调起。
- **AX 主路径（pyobjc Accessibility）** — `list_running_apps / activate_app / quit_app / list_windows / get_ax_tree / read_window_text / screenshot_window / click_ax_node / type_text / select_menu` 共 10 个工具。AX 树每次工具调用重新拉取，避免界面变化用旧节点。
- **Vision 兜底（LiteLLM multimodal）** — `vision_click(query)` / `vision_type(query, text)`：AX 找不到目标时截 focused window → 多模态 LLM 定位坐标 → `cliclick` 模拟点击。每次工具调用至多 1 次 Vision，避免无限重试。
- **node_ref 编码** — 把 AX 节点路径序列化成稳定字符串，跨工具调用复用。
- **App Automation permission_probe** — 启动时探测 Accessibility + Screen Recording 权限，缺失则在日志里指引用户去 macOS 系统设置授权。

### Added — Scheduler（M3-C）

- **Main Agent 定时任务工具** — `create_schedule / list_schedules / cancel_schedule`，支持 `once` (ISO datetime) / `interval` (秒 ≥ 60) / `cron` (五段表达式) 三种触发器；create/cancel 走 medium-risk confirm，list 不走。
- **Schedule / ScheduleNotification 表** — 持久化定时任务和触发结果。
- **ScheduleManager** — APScheduler AsyncIOScheduler 单例，与 FastAPI lifespan 绑定启停；lifespan 启动时 `rehydrate()` 把 DB 里的 Schedule 行重新挂回 scheduler（过去的 once 自动跳过），避免重启丢任务。
- **虚拟会话触发** — 触发到点时新建 `sched_{sid}_{ts}` 会话，过滤掉 `create/list/cancel_schedule + ask_user`（无人在线）后跑 Main agent，把摘要写入 ScheduleNotification。
- **Credential masking** — `CreateScheduleTool` 在落库前用 `CredentialGuard.mask` 清洗 instruction。
- **Notifications API** — `GET /notifications/unread`（可选 `origin_conv_id` 过滤）+ `POST /notifications/{id}/read`。
- **Schedules API** — `GET /schedules` + `DELETE /schedules/{id}`，让前端直接 list/cancel 而不必走 Main Agent 工具。
- **Web 通知中心 + 定时任务页** — 侧边栏铃铛（30s 轮询、未读 badge、点击跳虚拟会话并自动 mark-read）；`/schedules` 页面列出全部任务、单条取消。

### Added — Skill（M3-B）

- **Skill 体系** — `skill.yaml` 清单 + `prompt.md` 工作指令，封装"工具链编排"为可挂载工作流。
- **SkillManifest 解析** — pydantic 模型，validate_params 校验 required / enum / 未知键。
- **SkillRegistry** — 扫描 `~/.openmarvis/skills/` + 内置 builtins 目录，bad-yaml 跳过不毒化启动；user skill 可 shadow built-in。
- **UseSkillTool + run_skill** — Main 主入口；`SkillToolRegistry` 按 `allowed_tools` 白名单过滤 Main 的工具，进 skill 子会话只能调允许的工具。`skill_loaded` SSE 事件供前端可视化。
- **document_convert 内置示例** — md / docx / pdf 互转，依赖系统已装的 pandoc；pandoc 缺失时不静默 fallback，直接报错提示 `brew install pandoc`。
- **Skills API + 页面** — `GET /skills` 返回 manifest 摘要；`/skills` 页面列已安装 skill、risk badge、参数和允许工具折叠。

### Added — Timeline 面板（M3-D）

- **Timeline 右侧 sidebar** — 纯前端消费已有 SSE 事件，后端零改动。
- **useTimeline (zustand)** — `ingest(event, data)` 维护 agent 树 + tool-call 列表，activeStack 处理 sub_agent 嵌套；clear/toggleOpen 状态。
- **组件** — `TimelinePanel` / `AgentSection` / `ToolCallRow` / `RiskBadge` / `DurationLabel`；状态色 running 蓝闪 / ok 绿 / error 红 / warning 黄；展开 row 看 args + error。
- **ChatStream 集成** — `onEvent` 第一行即 `timeline.ingest`，对气泡渲染零影响；顶部 Activity 开关 show/hide。

### Changed

- Tool 基类增加 `skip_cmd_guard` + `assess_risk()` 钩子（v0.5 已有；本期 App Agent 工具大量使用）。
- `client` 测试 fixture 隔离到 `tmp_path`（之前共享 `~/.openmarvis/data.db`，rehydrate 会串味）。

### Dependencies

- 新增 `apscheduler>=3.10,<4.0`（scheduler）。
- 新增 `pyyaml>=6.0`（skill manifest）。
- 新增 `pyobjc-framework-Cocoa / Quartz / ApplicationServices >=10.3`（App Agent，macOS 专属）。
- macOS 系统依赖：`brew install cliclick`（vision_click/vision_type 兜底用）。

### Configuration

- 无新增 settings 段；Skill 目录默认 `<workspace.root>/skills/` + 包内 builtins，可被 user shadow。

## v0.5.0 — 2026-06-02

### Added
- **Browser Agent** — Playwright headed 浏览器自动化：navigate / click / fill / submit_form / wait_for_selector / screenshot / extract_text / list_elements / evaluate / current_url / go_back（共 11 个工具）；BrowserPool 支持 shared / per_conv 两种 profile 模式；2FA 启发式检测 + ask_user 交接。
- **Computer Agent** — macOS 用户权限范围操作（19 个工具）：system_info / disk_usage / list_processes / find_process / open_app / close_app / app_status / kill_process / volume_get/set/mute / brightness_get/set / clipboard_read/write / lock_screen / sleep_system / open_settings_pane / notification。clipboard_read 自动对疑似凭据脱敏。
- **Spotlight 工具** — `search_files_spotlight` 调 macOS mdfind，提供 file-agent 和 Main 两端可用的秒级本地搜索；支持 KIND_MAP 简写（pdf / image / code / ...）。
- **Tool 基类扩展** — `skip_cmd_guard` 类属性（osascript 包装绕过 CmdGuard）；`assess_risk()` 钩子（evaluate JS 内容感知升级）。
- **PendingAskRegistry 跨 Agent 共享** — browser-agent / computer-agent 可调 ask_user（v0.1.0 禁令解禁）。

### Changed
- SecurityGate.check 签名增加 `tool=` 关键字参数，消费 skip_cmd_guard + assess_risk。
- v0.1.0 工具调用 SecurityGate 时统一传 `tool=self`。

### Configuration
- 新增 `[browser]` 段：`headless` / `isolation_mode` / `viewport_*` / `default_timeout_ms` / `allowed_domains`。

### Dependencies
- 新增 `playwright>=1.45,<2.0`（首次安装后执行 `python -m playwright install chromium`）。

## v0.1.0 — 2026-06-01

- 首个公开版本。Main + File + Search Agent 完整闭环。详见 GitHub Release。
