# OpenMarvis v0.5.0 (M2) 设计文档

- **项目代号**: OpenMarvis
- **版本**: v0.5.0（M2）
- **创建日期**: 2026-06-02
- **作者**: bessie + Claude（brainstorming 产出）
- **状态**: Draft, 待用户复审
- **License**: Apache 2.0
- **目标平台**: macOS 14+
- **前置版本**: v0.1.0（Main + File + Search Agent，已发布）

---

## 0. 背景与目标

### 0.1 起源

v0.1.0 已交付 OpenMarvis 的"骨架"——Main Agent + File Agent + Search Agent + 完整的分层调度、卡片协议、三级安全模型。这一版（v0.5.0 / M2）在骨架之上长"血肉"：**让智能体能操作浏览器和 macOS 系统本身**。

### 0.2 目标

- 新增 **Browser Agent**：Playwright 驱动的 headed 浏览器自动化（登录态保留、表单填写、DOM 提取、截图、2FA 友好交接）。
- 新增 **Computer Agent**：macOS 用户权限范围内的系统操作（信息查询、进程管理、应用控制、音量/亮度/剪贴板、设置面板、锁屏/休眠/通知）。
- 新增 **Spotlight 工具**：`mdfind` 集成到 file-agent + Main Agent，秒级本地搜索。
- 在 v0.1.0 的安全责任链上扩展：`evaluate(js)` 内容感知风险升级、`clipboard_read` 自动脱敏、Browser 域名白名单（可选）、Computer 工具绕过 CmdGuard（已知安全包装）。

### 0.3 非目标（v0.5 不做）

| 项 | 归属 |
|---|---|
| App Agent（macOS UI 自动化、Android 模拟器） | M3 / v1.0.0 |
| Skill 体系（`use_skill` 动态加载） | M3 / v1.0.0 |
| 定时任务（APScheduler 持久化） | M3 / v1.0.0 |
| 前端工具调用 timeline 增强（可视化） | 推迟（明确砍掉本轮） |
| Browser headless 作为默认 | 推迟（config 可切，但不默认） |
| 需要 sudo 的 Computer 操作（wifi/防火墙/系统组件更新） | 推迟 |
| 自动 CAPTCHA 解锁（2Captcha 等第三方） | 永久不做（伦理 + 服务条款） |

### 0.4 路线图位置

| 版本 | 内容 | 状态 |
|---|---|---|
| v0.1.0 | Main + File + Search Agent | ✅ 已发布 |
| **v0.5.0**（本 spec） | **+ Browser + Computer + Spotlight** | **Draft** |
| v1.0.0（M3） | + App Agent + Skill + 定时任务 | 待 brainstorm |
| v1.5（Voice + RAG） / v2（Windows） / v3（Teams） / v4（Marketplace） | 各自独立 spec | 路线图 |

**永久不做**：Linux 平台。

---

## 1. 整体架构（在 v0.1.0 之上）

### 1.1 沿用的架构

- 单进程 FastAPI + asyncio
- Sub Agent 同进程串行（一时刻至多一个 Sub Agent 在运行）
- 工具调用走 SecurityGate 责任链
- 卡片协议 `mv-*`
- workspace 隔离 + 写入审计

### 1.2 新增的子系统

```
┌─────────────────────────────────────────────────────────────────┐
│  Main Agent (orchestrator)                                      │
│   · dispatch_task → ┐                                           │
└──────────────────────┴─────────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┬────────────────┐
       ▼               ▼               ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ file-agent   │ │ search-agent │ │ browser-agent│ │ computer-agt │
│ (v0.1.0)     │ │ (v0.1.0)     │ │  ★ v0.5      │ │  ★ v0.5      │
│ + spotlight  │ │              │ │              │ │              │
│   ★ v0.5     │ │              │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
                                          │
                                          ▼
                                  ┌──────────────────┐
                                  │  BrowserPool ★   │
                                  │   shared/per_conv│
                                  │   profile 管理   │
                                  └──────────────────┘
```

### 1.3 v0.1.0 规则放宽：ask_user 对 Sub Agent 解禁

v0.1.0 spec §4.4 写过 "Sub Agent 不可调用 ask_user"。但 v0.5.0 的两个新 Agent 都有强需求：

- **browser-agent** 遇到 2FA / CAPTCHA 需要让用户在 headed 窗口里手动完成
- **computer-agent** 的 `kill_process` / `sleep_system` 是高风险操作必须用户确认

方案：**`ask_user` 对所有 Sub Agent 开放**（不只是 Main）。`PendingAskRegistry` 仍由 Main Agent 持有的实例（通过 `ToolContext` 传递给所有子 Agent 的工具），保证一个 conv 内只有一套 ask_id 命名空间，前端答复路由唯一。

实现上：`SubAgentFactory.build()` 注入 `AskUserTool(registry=main_ask_registry)` 到 browser-agent 和 computer-agent 的 ToolRegistry。File / Search Agent 暂不需要（行为不变）。

仍禁用的工具：`dispatch_task` / `use_skill` / `create_scheduled_task` / `present_result` / `modify_scheduled_task`（沿用 v0.1.0）。

### 1.4 关键设计决策汇总

| 决策 | 选择 | 理由 |
|---|---|---|
| Browser/Computer 子 Agent 模型 | 独立 Sub Agent | 与 v0.1.0 的分层一致；Main Agent 只 dispatch_task 不直调底层 |
| Browser 头部 | Headed 默认（config 可切 headless） | 可观察、可交接、2FA 友好 |
| Browser profile | 共享 profile 默认；config `isolation_mode="per_conv"` 可切 | 个人助手定位需要登录态持久 |
| Browser 2FA | 检测后 `ask_user` 让用户在窗口里手动 | 不绕过验证、不接第三方破解 |
| Browser 截图协议 | 复用 `mv-image-gallery` | 不新增卡片类型 |
| Browser `evaluate(js)` | 保留，risk_level=medium；内容感知升 high（含 cookie/localStorage/fetch） | 不过度封死灵活性 |
| Computer 实现 | 各工具 subprocess 包装（osascript / system_profiler / pmset / pbpaste/pbcopy） | 不复用 ShellExecutorTool（CmdGuard 误伤）|
| Computer 范围 | 用户权限范围（无 sudo） | 工程量可控；M3+ 再扩 |
| Computer `clipboard_read` | 自动 CredentialGuard.redact() 后回写 LLM | 保护剪贴板凭据 |
| Spotlight 工具归属 | file-agent + Main Agent | Main 也能秒搜本地 |
| 版本号 | v0.5.0 | 跨版本跳，符合"MVP 后重大能力增量"语义 |

---

## 2. Browser Agent

### 2.1 Sub Agent 注册

新增 `agent_name = "browser-agent"`，加入 `DispatchTaskArgs.agent_name` 接受列表。`SubAgentFactory.build()` 增加分支。

### 2.2 工具集

只对 `browser-agent` 可见（`available_to = ("browser-agent",)`）：

| 工具 | 入参 | 行为 | 风险 |
|---|---|---|---|
| `navigate` | `url` | 跳转到 URL，等 networkidle，验证 allowed_domains | low |
| `click` | `selector` `nth=0` | 点击元素（自动 scrollIntoView） | medium |
| `fill` | `selector` `value` | 填表（focus + clear + type）；value 走 CredentialGuard | medium |
| `submit_form` | `form_selector?` | 提交表单（找不到 form 则回车） | medium |
| `wait_for_selector` | `selector` `timeout=10000` | 等元素出现 | low |
| `screenshot` | `full_page=false` `selector?` | 截图，写 `workspace/temp/screenshot_<ulid>.png`，emit `mv-image-gallery` 卡片 | low |
| `extract_text` | `selector` `nth=0` | 返回元素 innerText | low |
| `list_elements` | `selector` `attrs=["text"]` `max=50` | 返回所有匹配元素的指定属性 | low |
| `evaluate` | `script` | 在页面上下文执行 JS，返回 `JSON.stringify(result)` | **medium / high**（动态评估） |
| `go_back` | — | 浏览器后退 | low |
| `current_url` | — | 当前 URL（轻量状态检查） | low |

**禁用**：`open_new_tab` / `route_intercept` / 任意 file:// URL。

### 2.3 Profile 与会话生命周期

```
~/.openmarvis/
└── browser-profile/             # 默认共享，跨会话保留登录态
    └── (Playwright user_data_dir contents)
```

`config.toml`：

```toml
[browser]
headless = false                   # 默认 headed
isolation_mode = "shared"          # shared | per_conv
viewport_width = 1280
viewport_height = 800
default_timeout_ms = 10000
allowed_domains = []               # 空=允许所有；非空=只允许列出的（含子域）
```

**进程模型**：

- `BrowserPool`（singleton）管理 Playwright `BrowserContext`
- `shared` 模式：1 个 context 复用，首次 `dispatch_task(browser-agent)` 时 lazy launch
- `per_conv` 模式：按 `conv_id` 维护 context 字典
- 每次 dispatch 给 browser-agent 用新的 `Page`；page 在 dispatch 结束时 close（但 context 保留）
- BrowserPool 在 FastAPI lifespan shutdown 时 `context.close()`

### 2.4 2FA / CAPTCHA / 人工验证流程

```python
# 启发式 selector 库（apps/backend/openmarvis/browser/checks.py）
HUMAN_VERIFICATION_SELECTORS = [
    'iframe[title*="reCAPTCHA"]',
    'iframe[src*="hcaptcha"]',
    'input[name*="otp"]',
    'input[name*="verification"]',
    'input[autocomplete="one-time-code"]',
    '[data-testid*="captcha"]',
    'text=请验证您是否为真人',
    'text=Verify you are human',
]
```

`navigate` / `click` / `submit_form` 完成后调 `_check_human_verification(page)`：
1. 任一启发式 selector 在 3s 内匹配 → 立即触发交接流程：
   - 工具内部调 `screenshot()` 推 `mv-image-gallery` 卡片
   - 通过共享的 `PendingAskRegistry`（见 §1.3）发起 `ask_user` 询问（title="检测到人机验证，请在浏览器窗口完成后点击确认"，form_type="confirm"，options=[{"label":"我已完成"},{"label":"取消"}]）。Browser Agent 的 LLM 自己也能调 `ask_user` 工具达到同样效果；但 2FA 检测路径绕过 LLM 直接用 PendingAskRegistry 更可靠
2. 用户点 "我已完成" → 工具返回正常 result；下次工具调用前再次检查同样的启发式
3. 用户点 "取消" → `ToolResult(error="user_cancelled_2fa")`，browser-agent 终止本任务

### 2.5 截图实现

```python
async def screenshot(args, ctx):
    page = await pool.get_page(ctx.conv_id)
    fname = f"screenshot_{ulid.new().str.lower()}.png"
    path = ctx.workspace.temp_dir / fname
    if args.selector:
        await page.locator(args.selector).first.screenshot(path=str(path))
    else:
        await page.screenshot(path=str(path), full_page=args.full_page)
    body = f"[{fname}](<{path}>)"
    return ToolResult(
        content=f"已截图: {path}",
        cards=[Card(type="mv-image-gallery", payload=body)],
    )
```

### 2.6 错误处理

| 场景 | 策略 |
|---|---|
| `page.goto` 超时（默认 30s） | `ToolResult(error="page_load_timeout: {url}")`，不重试 |
| selector 找不到 | `wait_for_selector` 返回 timeout error；其他工具返回 `"未找到元素 {selector}"` |
| 页面崩溃（`page.crash`） | BrowserPool 重建当前 conv 的 context；返回 `error="page_crashed_pool_reset"` |
| context 启动失败 | Sub Agent BLOCKED；emit `error` 给 SSE |
| Stale element | 工具内 retry 1 次后报错 |
| 域名不在 allowed_domains | `navigate` 立即返回 `error="domain_blocked: {host}"` |

### 2.7 与 search-agent / web_fetch 的边界

`main_agent.md` 加段：

```
Browser Agent 触发场景：
- 需登录后才能看到的内容
- 多步表单填写（注册 / 下单 / 评论）
- 按钮点击驱动的多页跳转
- 需要在 GitHub/X/Notion 等账户里"做事"

非触发场景（用 web_fetch 即可）：
- 纯内容阅读 / 总结 / 摘要
- 不需要登录的公开页面
- 单次 GET 拿到的信息

不知道用哪个？默认 web_fetch；明确需要"点/填/登录"时才 dispatch browser-agent。
```

### 2.8 后端文件结构

```
apps/backend/openmarvis/
├── agents/sub/
│   └── browser_agent.py          # SubAgentFactory 支持 "browser-agent"
├── browser/
│   ├── __init__.py
│   ├── pool.py                   # BrowserPool（context 管理）
│   ├── tools.py                  # NavigateTool / ClickTool / FillTool / ... 全部
│   └── checks.py                 # 人机验证启发式库
└── prompts/
    └── browser_agent.md
```

### 2.9 新增依赖

- `playwright>=1.45`
- `make install` 后自动 `playwright install chromium`（或文档明示用户执行）

---

## 3. Computer Agent

### 3.1 Sub Agent 注册

新增 `agent_name = "computer-agent"`，加入接受列表。

### 3.2 工具集

只对 `computer-agent` 可见（`available_to = ("computer-agent",)`）：

| 工具 | 入参 | 实现 | 风险 |
|---|---|---|---|
| `system_info` | `verbose=false` | `system_profiler SPHardwareDataType SPSoftwareDataType SPDisplaysDataType -json` → verbose=false 时返摘要 | low |
| `disk_usage` | `path?=/` | `df -h <path>` | low |
| `list_processes` | `top_n=20` `sort_by="cpu"` | `ps aux` → 排序取前 N，cmdline 走 CredentialGuard 脱敏 | low |
| `kill_process` | `pid` | `kill <pid>`；PID < 200 或在 SAFE_PID 名单则拒绝 | **high**（ask_user） |
| `find_process` | `name_pattern` | `pgrep -fl <pattern>` | low |
| `open_app` | `app_name` | `open -a "<app>"` | low |
| `close_app` | `app_name` `force=false` | osascript `tell app "<name>" to quit`；`force=true` 走 `killall` | medium |
| `app_status` | `app_name` | osascript `running of application "<name>"` | low |
| `volume_get` | — | osascript `output volume of (get volume settings)` | low |
| `volume_set` | `level: 0-100` | osascript `set volume output volume <level>` | medium |
| `volume_mute` | `muted: bool` | osascript `set volume with/without output muted` | medium |
| `brightness_get` | — | osascript（display brightness via System Events） | low |
| `brightness_set` | `level: 0.0-1.0` | osascript（display brightness） | medium |
| `clipboard_read` | — | `pbpaste` → CredentialGuard.redact() | **medium** |
| `clipboard_write` | `text` | `pbcopy`；text 走 CredentialGuard | medium |
| `lock_screen` | — | osascript `keystroke "q" using {control down, command down}` | medium |
| `sleep_system` | — | osascript `tell app "System Events" to sleep` | **high**（ask_user） |
| `open_settings_pane` | `pane: Literal["sound","display","network","privacy","battery","general"]` | `open x-apple.systempreferences:com.apple.preference.<pane>` | low |
| `notification` | `title` `body` `subtitle?` | osascript `display notification` | low |

**禁用**：`shutdown` / `restart`（避免误操作；用户可手动）。

### 3.3 实现策略

每个工具是 `asyncio.create_subprocess_exec(...)` 的薄包装，**不复用 ShellExecutorTool**。每个工具自带 `skip_cmd_guard = True`：

```python
class Tool:
    name: ClassVar[str] = ""
    risk_level: ClassVar[str] = "low"
    available_to: ClassVar[Iterable[str]] = ()
    skip_cmd_guard: ClassVar[bool] = False   # 新增
```

`SecurityGate.check()`：

```python
if "command" in args and not tool.skip_cmd_guard:
    decisions.append(self.cmd_guard.check_command(args["command"]))
```

所有 osascript 调用走 `subprocess` 多参数模式（不拼字符串），杜绝注入：

```python
await asyncio.create_subprocess_exec(
    "osascript", "-e", f'set volume output volume {args.level}',
    ...
)
```

### 3.4 clipboard_read 脱敏

```python
async def execute(self, args, ctx):
    proc = await asyncio.create_subprocess_exec(
        "pbpaste", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    raw, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
    text = raw.decode("utf-8", errors="replace")
    redacted = CredentialGuard.redact_static(text)
    warn = ""
    if redacted != text:
        warn = "\n[已对疑似凭据脱敏；原始内容未传给模型]"
    return ToolResult(content=redacted + warn)
```

### 3.5 system_info 摘要格式（verbose=false）

```
========================
macOS 14.5 (23F79), MacBook Pro M2 Pro
CPU: Apple M2 Pro, 10 核
内存: 32 GB
存储: 800 GB 可用 / 1 TB
显示器: 1× 内建 Retina (3024×1964)
========================
当前 CPU 使用: 35%（用户 28% / 系统 7%）
当前内存压力: 22 GB used / 32 GB total
正在运行: 156 个进程
电池: 87%（充电中）
========================
```

`verbose=true` 返回完整 `system_profiler -json`，截断到 50KB。

### 3.6 后端文件结构

```
apps/backend/openmarvis/
├── agents/sub/
│   └── computer_agent.py         # SubAgentFactory 支持 "computer-agent"
├── computer/
│   ├── __init__.py
│   ├── tools_info.py             # system_info / disk_usage / list_processes / find_process
│   ├── tools_apps.py             # open_app / close_app / app_status / kill_process
│   ├── tools_settings.py         # volume_* / brightness_* / open_settings_pane
│   ├── tools_clipboard.py        # clipboard_read / clipboard_write
│   ├── tools_session.py          # lock_screen / sleep_system / notification
│   └── permission_probe.py       # 启动检测
└── prompts/
    └── computer_agent.md
```

### 3.7 错误处理

| 场景 | 策略 |
|---|---|
| osascript 报 "Not authorized" | `error="需要 macOS 辅助功能权限。前往 系统设置 > 隐私与安全性 > 辅助功能 添加 Python/Terminal"` |
| 进程不存在 | `error="PID {x} 不存在"` |
| 应用未运行 | `app_status` 返回 `running=false`；`close_app` 返回 `error="应用未运行"` |
| 命令超时（默认 30s） | `error="timeout: {command}"` |
| `kill_process` 命中 SAFE_PID 名单 | `error="拒绝 kill 系统关键进程 {name}"` |

### 3.8 权限引导

`permission_probe.py` 在 FastAPI lifespan 启动时调用：

```python
def probe_permissions(state):
    issues = []
    try:
        subprocess.run(["osascript", "-e", 'tell app "System Events" to return name'],
                        check=True, capture_output=True, timeout=5)
    except subprocess.CalledProcessError:
        issues.append("System Events 权限缺失")
    try:
        subprocess.run(["pbpaste"], check=True, capture_output=True, timeout=2)
    except subprocess.CalledProcessError:
        issues.append("剪贴板访问失败")
    for issue in issues:
        log.warning("Permission probe: %s", issue)
```

不阻塞启动；只 log warning，让 Main Agent 在用户首次触发相关工具时友好提示。

---

## 4. Spotlight 工具

### 4.1 工具

| 工具 | 入参 | 行为 | 风险 |
|---|---|---|---|
| `search_files_spotlight` | `query` `max_results=50` `onlyin?=path` `kind?=string` | `mdfind -onlyin <path> <query>` → 路径列表 + `mv-file-list` 卡 | low |

`available_to = ("main", "file-agent")` —— Main 也能秒搜本地。

### 4.2 实现

```python
KIND_MAP = {
    "pdf": "kind:pdf",
    "image": "kind:image",
    "audio": "kind:audio",
    "video": "kind:movie",
    "code": "kMDItemContentType == 'public.source-code'",
    "text": "kind:text",
    "word": "kind:words",
    "excel": "kind:numbers",
    "ppt": "kind:presentation",
}

class SpotlightTool(Tool):
    name = "search_files_spotlight"
    description = "用 macOS Spotlight (mdfind) 快速搜索本地文件，支持元数据和全文。"
    args_model = SpotlightArgs
    risk_level = "low"
    available_to = ("main", "file-agent")

    async def execute(self, args, ctx):
        cmd = ["mdfind"]
        if args.onlyin:
            decision = ctx.security.path_guard.check_path(args.onlyin)
            if decision.action == "block":
                return ToolResult(error=f"risk_blocked: {decision.reason}")
            cmd += ["-onlyin", args.onlyin]
        query = args.query
        if args.kind and args.kind in KIND_MAP:
            query = f"{KIND_MAP[args.kind]} {query}"
        cmd.append(query)
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        hits = (out or b"").decode("utf-8", errors="replace").splitlines()[: args.max_results]
        body = "\n".join(f"[{Path(p).name}](<{p}>)" for p in hits if p) or "（无匹配）"
        return ToolResult(
            content=f"Spotlight 找到 {len(hits)} 项",
            cards=[Card(type="mv-file-list", payload=body)] if hits else [],
        )
```

### 4.3 与 search_files 的边界（写入 main_agent.md）

```
- 不知道大致路径 / 只知文件名关键词 → search_files_spotlight（秒级）
- 知道具体目录 + 想全文搜索 → search_files（fnmatch + contains）
- 默认偏好 Spotlight；Spotlight 0 结果时 fallback 到 search_files
```

### 4.4 后端文件结构

```
apps/backend/openmarvis/tools/
└── spotlight.py                  # SpotlightTool
```

注册到 `agents/sub/factory.py`（file-agent）和 `agents/main_agent.py`（Main）。

---

## 5. 安全模型扩展

### 5.1 Browser 安全

| 风险 | 缓解 |
|---|---|
| 共享 profile → cookies 持久 → Agent 被诱导访问钓鱼站可复用登录态 | `[browser] allowed_domains` 配置（空=允许所有；非空=白名单含子域）；Main prompt 强制 navigate 前要求用户明示 URL |
| `evaluate(js)` 任意 JS 执行 | risk_level=medium → AI 自主提议时 SecurityGate 强制 ask_user；用户在 chat 里明示要求时直接执行 |
| `fill` 表单参数含密码/token | `value` 走 CredentialGuard；命中则 audit_log args_hash="REDACTED"；trace 显示 `[REDACTED]` |
| 截图含敏感页面 | 用户责任；不主动后处理 |

### 5.2 Computer 安全

| 风险 | 缓解 |
|---|---|
| 误杀关键进程（WindowServer / launchd / coreaudiod） | `kill_process` 内置 PID < 200 + SAFE_PID 名单；high → ask_user |
| `sleep_system` / `lock_screen` 误触发 | sleep=high（ask_user），lock=medium |
| osascript 注入 | 全部走 `subprocess.create_subprocess_exec` 多参数模式 |
| `clipboard_read` 泄露凭据 | 自动 `CredentialGuard.redact()`；原始内容不入 LLM 上下文 |
| `ps aux` cmdline 含密码 | 输出统一走 CredentialGuard.redact() |

### 5.3 SecurityGate 扩展

新增 `Tool.skip_cmd_guard: ClassVar[bool] = False`。`computer/*` 全部设 `True`。`SecurityGate.check()` 跳过 CmdGuard 对这些工具。

`evaluate(js)` 用 `assess_risk()` 钩子做内容感知：

```python
class EvaluateTool(Tool):
    name = "evaluate"
    risk_level = "medium"

    def assess_risk(self, args, ctx):
        risky = ("document.cookie", "localStorage", "sessionStorage", "fetch(", "XMLHttpRequest")
        if any(k in args.script for k in risky):
            return RiskAssessment(level="high",
                                  reasons=["JS 可能读取 cookie/storage 或外发请求"])
        return RiskAssessment(level="medium", reasons=[])
```

### 5.4 三档 security level 影响

| Level | 影响 v0.5 |
|---|---|
| `strict` | Browser `evaluate` 全部 ask_user；Computer 所有 medium 升 high |
| `normal`（默认） | 按上表 |
| `permissive` | medium 自动通过；high 仍 ask_user |

### 5.5 审计日志

`AuditLog` 表 schema 无变更（v0.1.0 字段够用）：

- Browser：`args_hash` 对 `fill.value` 命中凭据时记 `"REDACTED"`；其他参数正常哈希
- Computer：`clipboard_read` / `kill_process` / `sleep_system` 全量记录

---

## 6. 工期 + 测试 + 验收

### 6.1 阶段划分（M2，~3 周）

```
M2-A Browser Agent       → ~1.5 周（11 天）
M2-B Computer Agent      → ~1 周（7 天）
M2-C Spotlight + 整合     → ~3 天
M2-D 打磨 + 发版          → ~2 天
```

### 6.2 M2-A — Browser Agent (~11 天)

| 子任务 | 天数 |
|---|---|
| 装 playwright + BrowserPool 骨架（lazy launch / per-conv 切换） | 2 |
| 工具实现（navigate / click / fill / submit / wait_for_selector / current_url / go_back） | 2 |
| screenshot 工具 + mv-image-gallery 集成 | 1 |
| extract_text / list_elements / evaluate（含 risk 升级） | 1.5 |
| 2FA 检测 + ask_user 流程 + 启发式 selector 库 | 1.5 |
| browser_agent.md prompt + SubAgentFactory 接入 | 1 |
| 单测（mock playwright Page）+ 集成测（headed 真启动 1-2 个场景） | 2 |

### 6.3 M2-B — Computer Agent (~7 天)

| 子任务 | 天数 |
|---|---|
| Tool base.skip_cmd_guard 扩展 + 4 个文件分组（info / apps / settings / clipboard / session） | 2 |
| osascript / system_profiler / pmset 包装 + 单测 | 2 |
| permission_probe（启动检测 + warning） | 0.5 |
| clipboard_read 脱敏路径 | 1 |
| computer_agent.md prompt + SubAgentFactory 接入 | 0.5 |
| 集成测（真实 macOS：volume/brightness/clipboard 一次往返 + 还原） | 1 |

### 6.4 M2-C — Spotlight + 整合 (~3 天)

| 子任务 | 天数 |
|---|---|
| SpotlightTool 实现 + 单测（mock mdfind 输出） | 1 |
| 注册到 file-agent + Main Agent | 0.5 |
| 集成测（真实 mdfind） | 0.5 |
| Main Agent prompt 更新（spotlight vs search_files vs web_fetch 选择启发） | 1 |

### 6.5 M2-D — 打磨 + 发版 (~2 天)

- 全套 pytest + 覆盖率（目标维持 ≥85%）
- Playwright E2E 加 2 个新场景（"打开 GitHub 看仓库"、"调亮度"）
- README + CHANGELOG 更新（"v0.5.0 — Browser + Computer + Spotlight"）
- CI 跑通
- tag `v0.5.0`，建 GitHub Release 草稿

### 6.6 测试策略

**单测**（mock）：

- Browser 工具：mock `playwright.async_api.Page`，验证 selector/timeout/参数透传、return shape、2FA 检测分支
- Computer 工具：mock `subprocess.create_subprocess_exec`，验证 args + 解析逻辑
- Spotlight：mock mdfind 输出，验证 kind 映射 + 路径 onlyin 通过 PathGuard
- `EvaluateTool.assess_risk`：含 cookie/storage/fetch 时升 high；干净脚本保持 medium

**集成测**（真实，gated by env var `OPENMARVIS_M2_LIVE=1`）：

- Browser：启动 chromium、navigate example.com、截图、extract_text 拿 h1、close
- Computer：volume_get → volume_set(50) → volume_get → 还原；clipboard 往返；list_processes 看 python3 在
- Spotlight：mdfind 实际跑（搜 ~/Documents 下任意 .pdf）

**E2E**（Playwright，需 ANTHROPIC_API_KEY + OPENMARVIS_E2E_LIVE=1）：

- v0.1.0 的 3 场景仍跑
- 新增 "用 Browser Agent 打开 https://example.com 然后告诉我 h1 文本"
- 新增 "调整音量到 30%"

### 6.7 v0.5.0 验收清单

- [ ] 后端 pytest ≥85% 整体覆盖率（M2 新模块单独 ≥75%）
- [ ] Browser Agent 在 headed 模式跑通 example.com 全流程
- [ ] Computer Agent 能调音量/亮度/剪贴板/系统信息
- [ ] Spotlight 工具在 file-agent + Main 调用链里正常
- [ ] CI macos-14 runner 全绿（Browser 在 CI 用 headless）
- [ ] tag `v0.5.0` + GitHub Release 发出
- [ ] README 加 v0.5.0 Quick Start 段（"试试让 OpenMarvis 帮你查电池剩余"）

### 6.8 关键风险与缓解

| 风险 | 缓解 |
|---|---|
| Playwright headed 在无图形界面（CI macos-14）失败 | CI 跑 headless（环境变量覆盖），本地集成测仍 headed |
| macOS 辅助功能权限弹窗阻塞集成测 | permission_probe 先于工具调用；文档指引用户预先授权 |
| `[browser] allowed_domains` 改动需 BrowserPool 重启 | 文档明示；config reload 后续 plan |
| osascript macOS 14 vs 15 差异（display brightness API 变过） | 双版本 fallback；CI 测试矩阵不强求两套（只跑 14） |
| 集成测污染用户系统（音量变了） | fixture teardown 恢复原值（先 read → set → ... → set 回原值） |
| Browser context 内存泄漏 / page handle 未释放 | shutdown hook 强制 close；page 在 dispatch_task 结束时 try/finally close |

### 6.9 v0.5.0 → v1.0.0 衔接

v0.5.0 发版后立刻开始 M3 brainstorm。M3 的开放问题（写入 `.next-plan-todo.md`）：

- App Agent 选 pyobjc Accessibility API 还是 cliclick + screenshot+vision 混合？
- Android 模拟器集成是否值得（8GB 镜像、ADB 依赖）？
- Skill 体系内置示例选什么（PPT 生成？语音消息？）？
- 定时任务和 ScheduleWakeup pattern 复用程度？
- 是否需要前端工具调用 timeline 增强（M2 砍掉的）？

---

## 7. 开放问题（不阻塞 spec，在 plan 阶段或 v0.5 中确认）

1. Playwright Python binding 在 LiteLLM 同进程下的内存占用基线？M2-A 第 2 天验证。
2. macOS 14.5 vs 14.6 vs 15.x 上 `osascript display brightness` 是否一致？M2-B 第 1 天验证。
3. `clipboard_read` redact 后再 `clipboard_write` 同一会话是否需要"记忆"原始值（让用户问"我刚复制的密码是？"能拿回来）？v0.5 默认 No；视用户反馈在 v0.6 加。
4. BrowserPool 在 `isolation_mode="per_conv"` 时的 LRU 策略（最多保留 N 个 context）？v0.5 默认无 LRU，conv 删除时清理；视内存压力在 v0.6 加。

---

## 附录 A — v0.5.0 决策一览

| 维度 | 决策 |
|---|---|
| 版本号 | v0.5.0 |
| 范围 | Browser + Computer + Spotlight |
| Browser headed | 默认 headed（config 可切 headless） |
| Browser profile | shared 默认，per_conv 可切 |
| Browser 2FA | ask_user 让用户在窗口手动 |
| Browser 截图 | mv-image-gallery 复用 |
| Browser evaluate | 保留，risk_level=medium；内容感知升 high |
| Browser allowed_domains | 默认空（允许所有） |
| Computer 范围 | 用户权限（无 sudo） |
| Computer 19 个工具 | 见 §3.2 |
| Computer clipboard | 自动脱敏后回写 LLM |
| Computer kill_process | high + SAFE_PID 名单 |
| Computer sleep_system | high + ask_user |
| Computer 实现 | subprocess 包装 + skip_cmd_guard |
| Spotlight 工具 | file-agent + Main 都可见 |
| 测试覆盖率 | 维持 ≥85% |
| 工期 | 3 周 |
| 集成测污染恢复 | fixture teardown 还原 |

## 附录 B — 与 v0.1.0 的差异

| 维度 | v0.1.0 | v0.5.0 |
|---|---|---|
| Sub Agent 数 | 2（file/search） | 4（+ browser / computer） |
| 工具数 | 14 | 14 + 11 browser + 19 computer + 1 spotlight = **45** |
| 安全 Guard | 3 层（Path/Cmd/Credential） | 同 + Tool.skip_cmd_guard + assess_risk 动态升级 |
| 卡片类型 | 8 个 mv-* | 同（无新增） |
| 依赖 | fastapi/litellm/sqlmodel/... | + playwright |
| Browser 集成 | 无 | BrowserPool（shared/per_conv） |
| macOS 系统集成 | 无 | osascript / system_profiler / pmset 包装 |
| 本地搜索 | search_files (fnmatch) | + Spotlight (mdfind) |
