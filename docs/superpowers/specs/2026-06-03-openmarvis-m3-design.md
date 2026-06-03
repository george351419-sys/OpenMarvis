# OpenMarvis M3 / v1.0.0 设计 Spec

> **状态**：已批准（用户分节确认 §1–§7，2026-06-03）
> **范围**：在 v0.5.0 之上增量 4 个能力（App Agent / Skill / Scheduled / Frontend Timeline）+ 发布 v1.0.0
> **平台**：macOS 14+（Android 模拟器砍掉，留给 v2.0+ 路线）
> **工期**：6 周（31 工作日）
> **License**：Apache-2.0

---

## 1. 范围与定位

### 1.1 v1.0.0 = v0.5.0 + 四块拼图

| 模块 | 名称 | 工期 |
|---|---|---|
| **M3-A** | App Agent（macOS 桌面应用 UI 自动化，pyobjc Accessibility 主路径 + Vision LLM 兜底） | ~3 周 |
| **M3-B** | Skill 体系（`use_skill` 动态加载 + skill.yaml 清单 + 沙箱 + 1 个内置示例） | ~1 周 |
| **M3-C** | 定时任务（APScheduler + SQLite jobstore + 虚拟会话触发 + SSE 回写） | ~0.5 周 |
| **M3-D** | 前端 Timeline 面板（v0.5 已发 SSE 事件的纯前端可视化消费） | ~1 周 |
| **M3-E** | 发版（全测试 / Playwright / README / v1.0.0 tag / GitHub Release 草稿） | ~0.5 周 |

### 1.2 v1.0.0 完成后的项目状态

- **5 个 Sub Agent**：file / search / browser / computer / **app**(NEW)
- **~60 个工具**（v0.5 已有 45 + 本期新增 ~15）
- **3 个新机制**：Skill 动态加载、Scheduled 虚拟会话、Timeline 可观察性
- **macOS 全栈桌面 AI 助手能力闭环**（达成 Marvis 主功能对标）

### 1.3 整体架构（增量视角）

```
Main Agent
├─ Sub Agents: file / search / browser / computer / app(NEW)
├─ Skill Layer (NEW): use_skill → UseSkillSubAgent → 白名单工具
├─ Scheduler (NEW): APScheduler + jobstore → 触发"system trigger session" → 注入 chat SSE
└─ Tools: 45 → ~60，含 App Agent 12 工具 + 3 个 schedule 工具 + 1 个 use_skill

SSE 流新事件（小幅扩展，不破坏 v0.5 兼容性）：
  - schedule_trigger(NEW)   # 定时触发到原会话的提示
  - skill_loaded(NEW)       # use_skill 启动
```

### 1.4 v1.0.0 显式不做的事

- Android 模拟器集成（v2.0+）
- 第二个 Skill 内置示例（ppt_generate 留给 v1.x）
- Skill 包签名 / 自动 pip install / marketplace（v4.0）
- 定时任务的失败自动重试 / 任务依赖编排
- Windows / Linux 移植（v2.0 / 永不）
- Timeline 的 gantt 视图 / 导出 / 过滤器

---

## 2. App Agent（M3-A）

### 2.1 定位

第 5 个 Sub Agent。由 Main 通过 `dispatch_task("app-agent", ...)` 调起，专门处理"操作已经打开或可调起的 macOS 应用"。典型任务：在 Notes 建一条笔记、把 Music 切到指定曲、给 Mail 草稿加附件、Slack 里发条消息。

### 2.2 双层架构

```
┌───────────────────────────────────────────────────────────┐
│  App Agent (apps/backend/openmarvis/agents/sub/app_agent.py)
│  prompt: prompts/app_agent.md                              │
│  策略：先用 AX 树定位，找不到 → Vision 兜底                │
└───────────────────────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
┌──────────────────┐         ┌────────────────────────────┐
│ AXBackend         │         │ VisionBackend              │
│ (pyobjc)          │         │ (screenshot + LLM)         │
│ ─ list_windows    │         │ ─ screenshot_focused()     │
│ ─ get_ax_tree     │         │ ─ vision_locate(query, img)│
│ ─ click_ax_node   │         │ ─ cliclick / pyautogui     │
│ ─ type_in_field   │         └────────────────────────────┘
│ ─ select_menu     │
└──────────────────┘
```

- **AXBackend**：`pyobjc-framework-Accessibility` 拿 `AXUIElement`，通过 `AXUIElementCopyAttributeValue` 读 `AXTitle / AXRole / AXValue / AXChildren / AXEnabled`。每次工具调用都会重新拉一次目标窗口的 AX 树（不缓存跨调用），避免界面变化后用旧节点导致点错。
- **VisionBackend**：在 AX 树找不到目标控件时启动。截 focused window → 多模态 LLM（复用 `LiteLLMClient` 的 vision 能力）定位坐标 → `cliclick` 模拟点击。Vision fallback 只在 AX 明确"未找到"时触发，每个工具调用最多 1 次（避免无限重试）。

### 2.3 工具列表（12 个，全部位于 `app.*` namespace）

| 工具 | backend | 默认风险 | 说明 |
|---|---|---|---|
| `list_running_apps` | AX | low | 当前运行的 GUI 应用 |
| `activate_app(bundle_id)` | AX | low | 把 app 拉到前台 |
| `quit_app(bundle_id)` | AX | **medium** | 退出 app，要 confirm |
| `list_windows(bundle_id)` | AX | low | 该 app 所有窗口 |
| `get_ax_tree(bundle_id, max_depth=6)` | AX | low | 拉 AX 子树供 LLM 决策 |
| `click_ax_node(node_ref)` | AX | low | 按节点 ID 点击 |
| `type_text(node_ref, text)` | AX | low | 在文本框输入 |
| `select_menu(bundle_id, path=["File","New Note"])` | AX | low | 走菜单栏 |
| `read_window_text(bundle_id)` | AX | low | dump 窗口可见文本 |
| `screenshot_window(bundle_id)` | AX+Quartz | low | 截窗口 → 卡片回流前端 |
| `vision_click(query)` | Vision | **medium** | AX 找不到时兜底，自然语言定位+点击 |
| `vision_type(query, text)` | Vision | **medium** | 同上，定位输入框并填字 |

**节点引用协议**：`node_ref = "{bundle_id}|{window_index}|{ax_path}"`，`ax_path` 是 AX 节点在树里的索引路径（如 `"0/2/1/3"`）。每次工具调用前 App Agent 先 `get_ax_tree` 再用 ref；不持久化跨工具的 ref。

### 2.4 权限探测

扩展 `apps/backend/openmarvis/app_automation/permission_probe.py`：

```python
def check_accessibility() -> bool:
    """检查"系统设置 → 隐私 → 辅助功能"里是否授权 OpenMarvis"""

def check_screen_recording() -> bool:
    """vision 兜底需要屏幕录制权限"""
```

启动时探测 → 缺权限时通过 `warning` SSE 事件提示用户去授权；对应工具调用时直接返回 `permission_denied`，**不会走 SecurityGate**（节省一次 confirm 弹窗）。

### 2.5 prompt 纪律（prompts/app_agent.md）

1. **永远先 AX 后 Vision**：每个任务先 `get_ax_tree` 看结构，找到目标节点 → `click_ax_node / type_text`；只有 AX 树明确"未找到"才用 `vision_*` 工具。
2. **每次操作前 `read_window_text`** 确认当前态符合预期（防止前一步失败后继续盲操作）。
3. **不跨应用编排** —— 如需 file/web 操作，回报给 Main，由 Main 再派给 file/browser/search agent。
4. **解禁 `ask_user`**（同 v0.5 browser/computer）—— 遇到歧义（"哪个窗口"、"用哪个账号"）直接问。

### 2.6 安全增量

- `quit_app / vision_click / vision_type` 默认 medium，走 SecurityGate confirm。
- App Agent 的 Sub Agent 工具注入**不包含** `exec.shell / exec.python / fs.delete / fs.write_file`（隔离爆炸半径，要文件/命令时回 Main 派给其他 agent）。
- `type_text / vision_type` 的 `text` 参数过 CredentialGuard，发现 API key/密码格式拒绝（防止误把凭据输到错误窗口）。

---

## 3. Skill 体系（M3-B）

### 3.1 定位

把"常见复合任务"封装成可挂载的工作流模板，让 Main Agent 通过统一入口 `use_skill(name, params)` 调起。Skill 不是新工具类型，而是 **"工具链编排 + 提示词"的打包格式**。

### 3.2 目录约定

```
~/.openmarvis/skills/
└─ document_convert/           # 内置示例，安装时拷过去
   ├─ skill.yaml               # 清单：name, description, params schema, allowed tools
   ├─ prompt.md                # 这个 skill 的工作指令（给 LLM）
   ├─ scripts/                 # 可选：辅助 python 脚本（受沙箱约束）
   │  └─ pandoc_wrapper.py
   └─ tests/                   # 可选：作者写的 golden test
      └─ test_md_to_pdf.py
```

启动时后端扫 `~/.openmarvis/skills/*/skill.yaml`，进内存注册表；前端通过 `GET /api/skills` 列出。

### 3.3 skill.yaml 清单

```yaml
name: document_convert
version: 1.0.0
description: Convert documents between md/docx/pdf using pandoc + reportlab.
author: OpenMarvis
license: Apache-2.0

params:
  source_path:
    type: string
    description: Absolute path to source file
    required: true
  target_format:
    type: string
    enum: [md, docx, pdf]
    required: true
  output_dir:
    type: string
    description: Where to write result (default workspace/output)
    required: false

# 这个 Skill 在执行期允许调用哪些工具（白名单）
allowed_tools:
  - fs.read_file
  - fs.write_file
  - fs.list_dir
  - exec.shell        # 调 pandoc
  - present.product

# 风险声明，决定 use_skill 顶层是否 confirm
risk: medium
```

### 3.4 use_skill 协议

新增 1 个 main-level 工具：

```python
@register_tool
class UseSkillTool(Tool):
    name = "use_skill"
    namespace = "skill"
    risk_level = "low"   # Skill 本身风险由内部工具调用决定，顶层 confirm 由 skill.yaml.risk 决定

    async def execute(self, name: str, params: dict) -> ToolResult:
        skill = SkillRegistry.get(name)          # 不存在 → 报错
        skill.validate_params(params)            # 用 yaml schema 校验
        sub_agent = SubAgentFactory.create_skill_agent(
            skill_name=name,
            prompt=skill.prompt,                 # skill 的 prompt.md
            allowed_tools=skill.allowed_tools,   # 白名单
            params=params,
            workspace=self.workspace,
        )
        # SSE 流：发 skill_loaded(NEW) → sub_agent_start → ... → sub_agent_end
        return await sub_agent.run()
```

**关键约束**：Skill 子会话**只能调 allowed_tools**——`UseSkillSubAgent` 在每次 LLM 工具调用前过滤 tools 列表。等于在 Main 的 Tool registry 之上叠了一层白名单。

### 3.5 沙箱

- **路径**：Skill 工作目录限制在 `workspace.allowed_paths`（沿用 v0.5 PathGuard），不能读 `~/.openmarvis/skills/*`（外部代码）也不能写仓库目录。
- **脚本**：`scripts/*.py` 不会被 OpenMarvis 自动执行——它们只是 skill 作者写的辅助脚本，Skill 在 prompt 里通过 `exec.shell python scripts/foo.py` 显式调用，仍走 CmdGuard；CmdGuard 验证 python 脚本路径必须在 `~/.openmarvis/skills/{name}/scripts/` 下。
- **依赖**：v1.0 **不做自动 pip install**。skill.yaml 可声明 `requires_python_packages: [pandoc-bin]`，OpenMarvis 只在启动时检查并提示用户手装；不自动跑 pip。
- **签名**：v1.0 不做签名验证（YAGNI，留给 v4.0 marketplace）；本地用户加 skill 视为自己负责。

### 3.6 document_convert 内置示例

`prompt.md` 大致逻辑：

```
你是 document_convert skill。任务参数 {{params}}。

执行步骤：
1. 验证 source_path 存在且后缀符合常见文档格式
2. 推断 source_format（从扩展名）
3. 决定 output_path = output_dir / basename.target_format
4. 调 exec.shell：pandoc {source} -o {output}
   - 如果 target_format=pdf 且 pandoc 报错（缺 LaTeX），降级到 reportlab 简化路径
5. fs.read_file 检查输出大小 > 0
6. 调 present.product 声明产物，附路径 + 大小
7. 完成

异常处理：
- pandoc 不存在 → 报错并提示用户 brew install pandoc
- 路径越界 → PathGuard 自动拦截，直接报错给上游
```

CI 跑 3 个 pytest（md→pdf / md→docx / docx→md）。

### 3.7 前端

- 设置页加 "Skills" tab：已安装 skill 列表 + skill.yaml 摘要 + 启用/禁用开关。
- 聊天里新卡片 `mv-skill-call`（类似 `mv-tool-call`）：显示 skill name + params + 内部 tool_call 折叠列表 + 最终结果。

---

## 4. 定时任务（M3-C）

### 4.1 定位

让 LLM 能预约"30 分钟后提醒我"/"每周一早 9 点跑这个分析"/"2026-06-10 10:00 给我做个周报"。触发时**自动起一个新会话**执行预约时存的指令，结果通过 SSE 推送到原会话或当前在线会话。

### 4.2 调度器

```python
# apps/backend/openmarvis/scheduler/manager.py
class ScheduleManager:
    def __init__(self, db_path: Path):
        jobstore = SQLAlchemyJobStore(url=f"sqlite:///{db_path}/schedules.db")
        self._sched = AsyncIOScheduler(
            jobstores={"default": jobstore},
            timezone="local",
        )

    async def start(self): self._sched.start()
    async def shutdown(self): self._sched.shutdown(wait=False)

    def add_once(self, run_at: datetime, instruction: str, origin_conv_id: str) -> str: ...
    def add_interval(self, every_seconds: int, instruction: str, origin_conv_id: str) -> str: ...
    def add_cron(self, expr: str, instruction: str, origin_conv_id: str) -> str: ...
    def list(self) -> list[ScheduleRow]: ...
    def cancel(self, schedule_id: str) -> bool: ...
```

- 单进程 `AsyncIOScheduler`（FastAPI 主 loop 里跑），不要分布式。
- 持久化 `~/.openmarvis/schedules.db`，重启自动恢复。
- 3 类触发器（once / interval / cron）都支持。
- `interval` 最小间隔 60s（避免高频任务跑垮系统）。
- `cron / interval` 表达式严格校验，畸形直接拒绝。

### 4.3 数据表

```python
class Schedule(SQLModel, table=True):
    id: str = Field(primary_key=True)                                          # uuid
    origin_conv_id: str                                                        # 哪个会话创建的
    trigger_type: Literal["once", "interval", "cron"]
    trigger_spec: str                                                          # ISO datetime / seconds / cron expr
    instruction: str                                                           # LLM 待执行的自然语言指令（已脱敏）
    description: str                                                           # 给前端 UI 看的人类可读描述
    created_at: datetime
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_status: Literal["pending", "success", "failed"] | None
```

APScheduler 自己的 jobstore 表也在同库，两套表共享 sqlite 文件，互不干扰。

### 4.4 触发流程（虚拟会话）

```
[T 时刻 APScheduler fire]
    ↓
ScheduleManager._on_fire(schedule_id)
    ├─ load Schedule row (instruction, origin_conv_id)
    ├─ 创建 "system trigger conversation"：
    │   - conv_id = f"sched_{schedule_id}_{ts}"
    │   - parent_conv_id = origin_conv_id (元数据)
    │   - workspace = 新独立 workspace（隔离）
    │   - first_user_message = f"[Scheduled Trigger]\n{instruction}"
    ├─ 用 ChatService 跑这个会话（与正常会话同一通路）
    │   - 全套 Main / Sub Agent / Tool / SecurityGate
    │   - SSE 事件持久化进 db（不要求前端在线）
    └─ 完成后：
        - update Schedule.last_run_at / last_status
        - 如果 origin_conv_id 当前有 SSE 客户端订阅 → 推一条 schedule_trigger(NEW) 事件
            { schedule_id, conv_id, status, summary, link }
        - 前端收到 → 在原会话气泡里插一条系统提示 + 链接跳到 sched_xxx 会话
```

**设计要点**：
- **独立 conv_id** 避免污染原会话历史 / workspace。
- **离线也能跑**：APScheduler 与 ChatService 通过队列联动，不依赖前端在线。
- **结果回流**：原会话在线 → 推 SSE；离线 → 用户下次打开会话时通过 `GET /api/conversations/{id}/notifications` 拿到挂起通知（v1.0 复用现有 UI 入口提示，不做独立通知中心）。

### 4.5 Main Agent 新增 3 个工具

| 工具 | 风险 | 说明 |
|---|---|---|
| `create_schedule(trigger_type, trigger_spec, instruction, description)` | **medium** | 创建预约，confirm；trigger_spec 严格校验 |
| `list_schedules()` | low | 列当前所有 schedule |
| `cancel_schedule(schedule_id)` | **medium** | 取消，confirm |

工具组挂在 `scheduler.*` namespace。Main prompt 加一段："用户说定时类需求，先复述给用户确认时机和指令文本，再 create_schedule。"

### 4.6 安全 & 边界

- **写入面**：`instruction` 入库前过 CredentialGuard 脱敏（不直接拒绝——已脱敏的指令仍能跑）；脱敏命中时回流前端 warning。
- **执行面**：
  - 虚拟会话独立 workspace `~/.openmarvis/workspaces/sched_<id>/`。
  - 虚拟会话内**禁用 `scheduler.*` 工具组**（防递归生成 schedule），由 ChatService 在 `parent_type == "schedule"` 时从 registry 过滤。
  - 虚拟会话内**禁用 `ask_user` 工具**（无人在线时无法响应）——执行中若 sub agent 调 `ask_user` 直接返回 `ask_user_unavailable_in_scheduled_run`，由 sub agent prompt 处理。
- **失败重试**：v1.0 不自动重试，`last_status=failed` 时 schedule 维持原触发计划继续下次（interval/cron 不会因一次失败下线）。

### 4.7 前端

- 设置页加 "Scheduled Tasks" tab：列表 + 取消按钮 + 上次运行状态。
- 新卡片 `mv-schedule-created`（确认创建时回流）/ `mv-schedule-trigger-notice`（触发时推到原会话）。

---

## 5. 前端 Timeline 面板（M3-D）

### 5.1 定位

v0.5 只能看到聊天流里散落的 `mv-tool-call` 卡片，看不到一个 Sub Agent 完整执行轨迹的纵向时间线。新增**右侧 Timeline 面板**作为聊天主区的可观察性 sidebar。**纯前端消费已有 SSE 事件，后端零改动**。

### 5.2 布局

```
┌──────────────┬──────────────────────┬──────────────────┐
│ Conversations│ Chat Stream          │ Timeline Panel   │
│  (existing)  │  (existing bubbles)  │  (NEW)           │
│              │                      │                  │
│              │                      │ ▼ Main Agent     │
│              │                      │   ├─ dispatch    │
│              │                      │   │   ▼ Browser  │
│              │                      │   │     ├─ goto  │
│              │                      │   │     ├─ click │
│              │                      │   │     └─ extract
│              │                      │   ├─ present_…   │
│              │                      │   └─ done        │
└──────────────┴──────────────────────┴──────────────────┘
       260px            flex-1               360px
```

- **Toggle 按钮**：聊天头部右上角加图标，点击 show/hide timeline；状态记 Zustand store，刷新保留。
- **响应式**：窗口窄时（<1280px）默认折叠成抽屉。

### 5.3 数据源（不增加后端新事件）

| SSE 事件 | timeline 表现 |
|---|---|
| `sub_agent_start` | 新建一个折叠区，头部显示 agent name + 任务标题（取自 dispatch payload） |
| `tool_call_start` | 在当前区底加一条 row：tool name + 折叠参数 + spinner |
| `tool_call_result` | 同一 row 填入耗时、状态颜色（绿=ok / 红=error / 黄=warning）+ risk badge |
| `sub_agent_end` | 折叠区头部加总耗时 + 总工具数 + 状态 |
| `ask_user` | 在 row 上挂"⏸ 等待用户输入"标记，链接跳到对应 `mv-ask-user` 卡片 |
| `card` (mv-product) | row 旁加 📎 图标，hover 显示文件名 |
| `warning` | 当前 agent 区头部加 ⚠ |
| `error` | 当前 row 红色 + error message tooltip |
| `done` | 顶层 Main Agent 区显示完成 |

### 5.4 状态层

```typescript
// apps/web/lib/stores/timeline.ts (NEW)
interface AgentNode {
  id: string;                    // sub_agent_id 或 "main"
  name: string;                  // "main" | "browser-agent" | ...
  taskTitle?: string;            // 由 dispatch payload 提供
  startedAt: number;
  endedAt?: number;
  status: "running" | "done" | "warning" | "error";
  parentId?: string;             // 嵌套关系
  toolCalls: ToolCallEntry[];
  warnings: string[];
}

interface ToolCallEntry {
  id: string;                    // tool_call_id（v0.5 已有）
  toolName: string;
  argsPreview: string;           // JSON 截断到 200 char
  startedAt: number;
  endedAt?: number;
  status: "running" | "ok" | "error";
  riskLevel?: "low" | "medium" | "high";
  errorMessage?: string;
  cardId?: string;               // 关联的 mv-card id
}

useTimelineStore: {
  agents: Record<string, AgentNode>;
  rootAgentId: string;
  ingest(event: SSEEvent): void;
  clear(): void;
}
```

ChatStream 组件在已有 SSE 接收循环里同步调用 `timeline.ingest(event)`，不影响主气泡渲染。

### 5.5 组件结构

```
apps/web/components/timeline/
├─ TimelinePanel.tsx           # 容器 + 滚动 + toggle 头
├─ AgentSection.tsx            # 一个 sub agent 折叠区
├─ ToolCallRow.tsx             # 单个工具调用 row
├─ RiskBadge.tsx               # low/medium/high 颜色徽章（slate/amber/red）
├─ DurationLabel.tsx           # 700ms / 1.2s / 12s（自动单位）
└─ TimelineEmpty.tsx           # 空态
```

UI 复用 shadcn `Collapsible / Tooltip / Badge`。

### 5.6 跳转 & 联动

- 点 ToolCallRow → 聊天主区滚到对应 `mv-tool-call` 卡片并高亮 1 秒（`scrollIntoView` + 临时 outline 类）。
- 点 ask_user 标记 → 滚到对应 `mv-ask-user` 卡片，焦点送到输入框。
- 切会话时 `store.clear()` + 从 conversation history 重放历史事件（已存 db）回填 timeline。

### 5.7 性能

- 长任务（>200 tool calls）虚拟滚动：`@tanstack/react-virtual` 包 ToolCallRow 列表。
- 不持久化到 localStorage——每次从会话 SSE 历史重建。
- 唯一新依赖：`@tanstack/react-virtual`。

### 5.8 不做的事（YAGNI）

- 不做 gantt 图 / 平行时间轴
- 不做 export timeline（JSON / 截图）
- 不做 filter（按 agent / 按 risk）

---

## 6. 安全模型增量

v1.0 **不引入新的 Guard 层**，沿用 v0.5 的三层 SecurityGate（PathGuard / CmdGuard / CredentialGuard）+ `Tool.assess_risk` 动态升级机制。

### 6.1 App Agent 安全

- **风险默认**：见 §2.3。
- **type_text / vision_type** 的 `text` 参数过 CredentialGuard，发现凭据格式拒绝。
- **工具白名单**：App Agent 的 Sub Agent registry 不注入 `exec.shell / exec.python / fs.delete / fs.write_file`。
- **权限缺失**：AX 工具直接返回 `permission_denied`，不进 SecurityGate（节省一次 confirm 弹窗）。

### 6.2 Skill 安全

- `UseSkillSubAgent` 启动时按 `skill.yaml.allowed_tools` 过滤 ToolRegistry 注入；LLM 看不到白名单外工具。
- 白名单工具仍走完整 SecurityGate（不绕过任何 Guard）。
- `skill.yaml.risk` 决定 use_skill 顶层 confirm：
  - `low` → 不 confirm
  - `medium` → confirm 一次
  - `high` → confirm + dry-run 选项（v1.0 留接口不强制实现）
- skill.yaml 解析失败 / schema 无效 / allowed_tools 含不存在工具 → 注册时拒绝，启动日志报 warning，**不让 LLM 看见这个 skill**。
- `scripts/*.py` 不自动执行；exec.shell 调用时 CmdGuard 验证脚本路径必须在 `~/.openmarvis/skills/{name}/scripts/` 下。

### 6.3 Scheduled 安全

- `create_schedule.instruction` 入库前过 CredentialGuard 脱敏。
- `cron / interval` 表达式严格校验；`interval` 最小 60s。
- 虚拟会话独立 workspace；禁用 `scheduler.*` 工具组（防递归）；禁用 `ask_user`（无人响应）。

### 6.4 Frontend Timeline 安全

无后端安全增量；risk badge 显示读自 `tool_call_result.risk_level`（v0.5 已发）。

### 6.5 全局不变

- 三层 Guard 不动（PathGuard / CmdGuard / CredentialGuard）。
- 不引入新 risk level（仍是 low / medium / high）。
- 不引入新 SSE 安全事件类型。
- 全局信息保护原则不变（never leak system prompt 等，沿用 v0.1 spec 安全章节）。

---

## 7. 工期 & 验收

### 7.1 子项工期细化（总 31 工作日 ≈ 6 周）

**M3-A · App Agent · ~3 周（15 工作日）**

| 子项 | 工作日 |
|---|---|
| pyobjc deps 接入 + permission_probe 扩展（Accessibility / Screen Recording） | 1 |
| AXBackend：list_windows / get_ax_tree / read_window_text / list_running_apps / activate_app + 单测 | 3 |
| AXBackend：click_ax_node / type_text / select_menu / screenshot_window + 单测 | 3 |
| VisionBackend：vision_locate + cliclick 包装 + vision_click / vision_type + 单测（mock LLM） | 2 |
| App Agent prompt + SubAgentFactory 注入 + 集成测试 | 2 |
| quit_app + risk 调优 + medium-risk confirm 流走通 | 1 |
| Playwright/手测：Notes / Music / Mail / Slack 4 场景 golden | 2 |
| Lint + 覆盖率达标 | 1 |

**M3-B · Skill 体系 · ~1 周（5 工作日）**

| 子项 | 工作日 |
|---|---|
| SkillRegistry / skill.yaml schema / 启动扫描 + 单测 | 1.5 |
| UseSkillTool + UseSkillSubAgent（白名单工具过滤）+ SSE skill_loaded 事件 | 1.5 |
| document_convert 内置示例（prompt + 3 个 pytest：md→pdf/docx，docx→md） | 1 |
| 前端 Settings/Skills tab + mv-skill-call 卡片 | 1 |

**M3-C · 定时任务 · ~0.5 周（3 工作日）**

| 子项 | 工作日 |
|---|---|
| APScheduler 集成 + ScheduleManager + SQLite jobstore + 3 触发器 + 单测 | 1 |
| 3 工具 + Main prompt 更新 + ChatService 虚拟会话路径 | 1 |
| 前端 Settings/Schedules tab + mv-schedule-* 卡片 + 离线挂起通知接口（GET /api/conversations/{id}/notifications） | 1 |

**M3-D · 前端 Timeline · ~1 周（5 工作日）**

| 子项 | 工作日 |
|---|---|
| useTimelineStore + ingest 逻辑 + 单测（jest ingest 多场景） | 1.5 |
| 组件：TimelinePanel / AgentSection / ToolCallRow / RiskBadge / DurationLabel + Storybook 样例 | 2 |
| ChatStream 接入 + toggle + 切会话历史重放 | 1 |
| 虚拟滚动接入（@tanstack/react-virtual）+ E2E"长任务 100+ tool calls" | 0.5 |

**M3-E · 发版 · ~0.5 周（3 工作日）**

| 子项 | 工作日 |
|---|---|
| 后端 pytest 全绿 + 覆盖率 ≥ 88% | 1 |
| 前端 typecheck + production build + 2 个 Playwright 新场景（App Agent + Skill） | 1 |
| README/CHANGELOG/.next-plan-todo 更新 + v1.0.0 tag + GitHub Release 草稿 | 1 |

### 7.2 任务顺序

```
M3-A App Agent ──┐
M3-B Skill     ──┼──► M3-D Timeline ──► M3-E 发版
M3-C Scheduled ──┘
```

A/B/C 互相独立；**D 必须放后面**（依赖 A/B/C 产生的新 SSE 事件做兼容验证）；E 收尾。

**推荐顺序**：A → C → B → D → E。

### 7.3 测试 & 验收门槛

- **后端覆盖率**：整体 ≥ 88%；新模块 ≥ 85%：
  - `app_automation/` ≥ 85%
  - `scheduler/` ≥ 90%
  - `skills/` ≥ 88%
- **前端**：`pnpm typecheck:web` 全过；`pnpm build:web` Compiled successfully；timeline 组件至少 1 个 jest 测试覆盖 ingest 路径。
- **Playwright E2E 新增 2 场景**：
  1. App Agent："打开 Notes 新建一条标题为 'OpenMarvis test' 的笔记并写入正文 → 校验 read_window_text 返回包含正文"
  2. Skill："use_skill document_convert，把 workspace/uploads/sample.md 转成 pdf → 校验 mv-product 产物存在 > 0"
- **CI**（GitHub Actions macos-14）全绿。
- **手动验收清单**：
  1. App Agent 在未授权 Accessibility 时显示明确提示
  2. Skill 列表能从 Settings 看到 + 启停切换
  3. 定时任务："1 分钟后提醒我"能跑通且不堵塞前端
  4. Timeline 在长会话下不卡顿
  5. 离线 schedule 触发，下次打开会话能看到挂起通知

### 7.4 发版 checklist

- [ ] 所有测试绿
- [ ] CHANGELOG.md 写完 v1.0.0 章节
- [ ] README.md 顶部 badge 改 v0.5.0 → v1.0.0
- [ ] `.next-plan-todo.md` 更新（v2.0 候选：Windows 移植 / RAG / voice）
- [ ] `git tag v1.0.0 && git push --tags`
- [ ] `gh release create v1.0.0 --draft --notes-file .release-notes-v1.0.0.md`
- [ ] 等待用户手动发布

---

## 8. 与 v0.5 / v0.1 协议的兼容性

- **SSE 协议**：v0.5 已发事件零变更；新增 `skill_loaded / schedule_trigger` 两个事件，老前端不识别会忽略（向后兼容）。
- **Tool 基类**：v0.5 的 `skip_cmd_guard / assess_risk / RiskAssessment` 全部保留；App Agent 工具不需要 skip_cmd_guard（不调 exec），medium-risk 通过默认 `risk_level` 标记。
- **SecurityGate**：三层 Guard 接口不变；新增的过滤逻辑（Skill 白名单 / Scheduled 虚拟会话工具过滤）发生在 Sub Agent registry 注入时，**早于 SecurityGate**，等于一道前置闸门。
- **Workspace 协议**：`~/.openmarvis/workspaces/conv_<id>/{uploads,temp,output}/` 保留；新增 `workspaces/sched_<id>/` 同结构。
- **CLI / make targets**：v0.5 `make install / dev / test` 全部继续可用；v1.0 新增 `make install:skills`（拷贝内置 skill 到 `~/.openmarvis/skills/`）。

---

## 9. 风险登记

| 风险 | 影响 | 应对 |
|---|---|---|
| AX 树在非标准 UI 应用上不可用（Electron / 自绘） | App Agent 部分场景失效 | Vision fallback 兜底；prompt 提示用户哪些应用更可靠 |
| pyobjc + Accessibility 权限授予流程跨 macOS 版本不一致 | 用户首次设置卡壳 | README 出详细授权步骤截图；permission_probe 给明确错误指引 |
| Vision LLM 定位坐标误差 | vision_click 点错 | 强制 medium-risk confirm；prompt 鼓励先 read_window_text 校准 |
| APScheduler jobstore 数据库锁竞争 | 高频 schedule 偶发失败 | `interval` 最低 60s；单进程串行 fire；写测试覆盖并发 |
| Skill 内 exec.shell 滥用（用户自装的恶意 skill） | 用户数据风险 | 启动时 warning 提示"加载第三方 skill 风险自负"；高 risk 默认 confirm |
| Timeline 组件渲染长任务卡顿 | 前端体验下降 | 虚拟滚动；E2E 100+ tool calls 性能验收 |
| Playwright 在 CI macos-14 不稳定 | 发版门槛 flaky | E2E 失败 retry 1 次；保留 v0.5 的现有 3 场景作为基线 |

---

## 10. 待 spec 之后

spec 批准后 → 转 `superpowers:writing-plans` skill 产出 M3 实施计划 → 用户批准 plan → 转 `subagent-driven-development` skill 按 plan 顺序执行。
