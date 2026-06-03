# Changelog

## Unreleased — v0.6.0

### Added
- **Scheduler** — Main Agent 三件工具 `create_schedule / list_schedules / cancel_schedule`，支持 `once` (ISO datetime) / `interval` (秒 ≥ 60) / `cron` (五段表达式) 三种触发器；create/cancel 走 medium-risk confirm，list 不走。
- **Schedule / ScheduleNotification 表** — 持久化定时任务和触发结果；`store/notifications.py` 提供 persist / list_unread / mark_read 三个 helper。
- **ScheduleManager** — APScheduler AsyncIOScheduler 单例，与 FastAPI lifespan 绑定启停；on_fire 回调驱动虚拟会话执行。
- **Virtual-conversation trigger runner** — 触发器到点时新建 `sched_{sid}_{ts}` 会话，过滤掉 `create/list/cancel_schedule + ask_user`（无人在线）后跑 Main agent，把摘要写入 ScheduleNotification。
- **Credential masking on schedule** — `CreateScheduleTool` 在落库前用 `CredentialGuard.mask` 清洗 instruction，避免凭据被持久化到 trigger payload。
- **Notifications API** — `GET /notifications/unread`（可选 `origin_conv_id` 过滤）+ `POST /notifications/{id}/read`。
- **Web 通知中心** — 侧边栏铃铛 + 未读 badge，30s 轮询，点击单条跳到虚拟会话并自动 mark-read，点击外部关闭。

### Configuration
- 无新增配置项；ScheduleManager 用 MemoryJobStore + SQL 表，DB 位置沿用 `workspace.root`。

### Dependencies
- 新增 `apscheduler>=3.10,<4.0`。

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
