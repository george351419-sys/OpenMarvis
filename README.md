# OpenMarvis

> 开源桌面 AI 智能体框架 · macOS · Apache 2.0

OpenMarvis 是一个可在本地运行的桌面 AI 助手，对标商业产品 [Marvis](https://marvis.app)，完全开源、可自部署、可扩展。它采用 **Main Agent → Sub Agent → Skill → Tool** 四级调度架构，将大语言模型与本地系统能力深度融合——读写文件、操控浏览器、调用 macOS API、执行定时任务，全部在用户设备上完成，无需将数据上传至第三方。

```
┌─────────────────────────────────────────────────────────┐
│                     OpenMarvis                          │
│   Next.js 前端  ←→  FastAPI 后端  ←→  SQLite 本地数据库   │
│                       ↕                                 │
│            Claude / DeepSeek / 混元 LLM                 │
│                       ↕                                 │
│        文件系统 / 浏览器 / macOS API / 第三方 App         │
└─────────────────────────────────────────────────────────┘
```

---

## 目录

- [架构总览](#架构总览)
- [技术栈](#技术栈)
- [数据流转逻辑](#数据流转逻辑)
- [核心模块详解](#核心模块详解)
- [与 Marvis 的对比与差异](#与-marvis-的对比与差异)
- [快速开始](#快速开始)
- [能力一览](#能力一览)
- [安全模型](#安全模型)
- [测试](#测试)
- [路线图](#路线图)
- [欢迎贡献](#欢迎贡献)

---

## 架构总览

OpenMarvis 分为三层：**前端（Web/Desktop）**、**后端（API + Agent）**、**数据层（SQLite + 文件系统）**。

```
┌──────────────────────────────────────────────────────────────────┐
│  前端层（apps/web · Next.js 14）                                   │
│                                                                    │
│  页面路由                  组件                      状态管理       │
│  /          首页            ChatStream               Zustand       │
│  /c/[id]    对话页          MessageBubble            useChat       │
│  /schedules 自动任务        TimelinePanel            useTimeline   │
│  /skills    技能广场        NotificationBell         useFilePreview│
│  /docs      文档授权        ConversationSidebar                    │
│  /download  客户端下载      FileUploader                           │
└─────────────────────┬────────────────────────────────────────────┘
                       │  HTTP + Server-Sent Events (SSE)
                       │  /api/proxy/* → Next.js 反向代理
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  后端层（apps/backend · FastAPI + Python 3.11）                   │
│                                                                    │
│  API 路由                   Agent 层                              │
│  POST /chat         ──────► MainAgent                             │
│  GET /conversations          ├── FileAgent (sub)                  │
│  PATCH /conversations/{id}   ├── SearchAgent (sub)                │
│  POST /files/upload          ├── BrowserAgent (sub)               │
│  GET /schedules              ├── ComputerAgent (sub)              │
│  POST /notifications         └── AppAgent (sub)                   │
│  GET /skills                                                      │
│  GET /settings                工具层（30+ tools）                  │
│                               fs / web / exec / spotlight / ...   │
│                                                                    │
│  基础设施                                                          │
│  ScheduleManager（APScheduler）  SkillRegistry  SecurityGate      │
└─────────────────────┬────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  数据层                                                            │
│  SQLite（SQLModel）        文件系统                                │
│  Conversation              ~/.openmarvis/workspace/{conv_id}/      │
│  Message                   └── uploads/   ← 用户上传              │
│  MemoryEntry（长期记忆）    └── temp/      ← 中间产物              │
│  Schedule                  └── output/    ← 最终产出              │
│  ScheduleNotification                                              │
│  AuditLog / WriteAudit                                             │
│  FTS5 虚拟表（全文索引）                                           │
└──────────────────────────────────────────────────────────────────┘
```

### 目录结构

```
copymarvis/
├── apps/
│   ├── backend/             # FastAPI 后端
│   │   └── openmarvis/
│   │       ├── agents/      # Main Agent + Sub Agent 工厂
│   │       ├── api/         # HTTP 路由（chat / conversations / files...）
│   │       ├── browser/     # Playwright 浏览器工具集
│   │       ├── computer/    # macOS 系统工具集
│   │       ├── app_automation/ # AX + Vision 第三方 App 自动化
│   │       ├── llm/         # LiteLLM 客户端 + EventSink（SSE 队列）
│   │       ├── memory/      # 长期记忆存储
│   │       ├── protocol/    # SSE 事件协议 + 卡片类型定义
│   │       ├── scheduler/   # APScheduler 定时任务管理
│   │       ├── security/    # PathGuard / CmdGuard / CredentialGuard
│   │       ├── skill/       # Skill 框架（manifest / registry / runner）
│   │       ├── store/       # SQLite 数据层（SQLModel）+ FTS5
│   │       ├── tools/       # 30+ 具体工具实现
│   │       └── workspace/   # 每次对话的文件工作区
│   ├── desktop/             # Electron 桌面客户端
│   └── web/                 # Next.js 14 前端
│       ├── app/             # App Router 页面
│       ├── components/      # React 组件
│       └── lib/             # API 客户端 / Zustand store / SSE 解析
└── docs/                    # 设计文档 + Marvis 对标规范
```

---

## 技术栈

### 后端

| 层次 | 技术选型 | 用途 |
|------|---------|------|
| Web 框架 | **FastAPI** + uvicorn | 异步 HTTP + SSE 长连接 |
| LLM 接入 | **LiteLLM** | 统一适配 Claude / DeepSeek / 混元 / OpenAI 等 |
| 数据库 | **SQLite** + **SQLModel** + **FTS5** | 对话历史、任务、通知、全文检索 |
| 浏览器自动化 | **Playwright** | 网页操作、截图、内容提取 |
| 定时任务 | **APScheduler** | once / interval / cron 三种触发器 |
| 系统能力 | **macOS AX API** + **cliclick** | 辅助功能 UI 自动化 |
| 文件处理 | **pandoc** / **pdfplumber** / **openpyxl** / **python-pptx** | 多格式文档转换与解析 |
| 安全 | 自研 PathGuard + CmdGuard + CredentialGuard | 三层防护 |

### 前端

| 层次 | 技术选型 | 用途 |
|------|---------|------|
| 框架 | **Next.js 14** App Router | SSR + 客户端组件混合 |
| 样式 | **Tailwind CSS** + shadcn/ui | 设计系统 |
| 状态 | **Zustand** | 跨组件对话状态 + Timeline 状态 |
| 流式通信 | 原生 **Fetch API + ReadableStream** | SSE 事件解析，支持中止 |
| 桌面 | **Electron** | 原生桌面窗口（macOS hiddenInset 标题栏） |

---

## 数据流转逻辑

### 1. 用户发送消息 → 流式响应

```
用户输入 (textarea)
    │
    ▼
ChatStream.send()
    │  POST /api/proxy/chat  {conv_id, message, attachments}
    ▼
Next.js 代理 /api/proxy/[...path]/route.ts
    │  透传到 http://127.0.0.1:8000/chat
    ▼
FastAPI POST /chat
    │  1. 从 SQLite 加载历史 Message 列表
    │  2. 构建 MainAgent（注入所有 Tool + SecurityGate）
    │  3. 创建 QueueEventSink（异步队列）
    │  4. asyncio.create_task(agent.run())
    │  5. 返回 EventSourceResponse，drain 队列 → SSE
    ▼
MainAgent.run()
    │  调用 LiteLLM → Claude/DeepSeek/混元
    │  ├─ thinking_delta  → emit("thinking_delta", {text})
    │  ├─ content_delta   → emit("content_delta", {text})
    │  ├─ tool_call       → 执行工具
    │  │   ├─ emit("tool_call_start", {call_id, name, args})
    │  │   ├─ tool.run()  （可能递归调用 Sub Agent）
    │  │   └─ emit("tool_call_result", {call_id, ok, preview})
    │  ├─ card            → emit("card", {type, payload})
    │  └─ done            → emit("done", {})
    ▼
前端 streamChat() 解析 SSE
    │
    ├─ thinking_delta   → store.appendThinking()
    ├─ content_delta    → store.appendContent()
    ├─ tool_call_start  → store.toolStart() + timeline.ingest()
    ├─ tool_call_result → store.toolResult() + timeline.ingest()
    ├─ card             → store.pushCard()  → 渲染专用卡片组件
    └─ done             → store.finishTurn()
```

### 2. Sub Agent 调度

```
MainAgent 遇到复杂任务
    │
    ▼
dispatch_task(target="file-agent", task="整理 ~/Downloads")
    │
    ▼
SubAgentFactory.create("file-agent")
    │  注入特定工具子集（文件 + 搜索工具）
    │  加载 file-agent 专属 System Prompt
    ▼
FileAgent.run()
    │  独立的 LLM 对话循环
    │  工具调用结果写入 SubAgentRecord
    ▼
结果返回 MainAgent
    │  MainAgent 综合子代理结果 → 继续回复用户
    ▼
前端收到 sub_agent_start / sub_agent_end 事件
    └─ Timeline 面板实时展示调度树
```

### 3. Skill 执行流程

```
用户: "帮我整理这堆 PDF"
    │
MainAgent 调用 use_skill("file_organizer", {target_dir: "..."})
    │
    ▼
SkillRegistry 加载 skill/builtins/file-organizer/
    │  读取 manifest.yaml（工具白名单 / 参数定义）
    │  读取 prompt.md（skill 专属指令）
    ▼
SkillRunner 创建专用 AgentBase
    │  只注入 manifest.allowed_tools 中的工具
    │  用 skill prompt 替换系统提示词
    ▼
Skill Agent 执行（可访问：list_dir / search_files / ask_user / write_file...）
    │  ask_user → 前端弹出确认卡片 → 用户勾选后继续
    ▼
执行完成，结果返回 MainAgent
```

### 4. 定时任务触发

```
用户对话: "每天早上 9 点提醒我开会"
    │
MainAgent 调用 create_schedule(trigger_type="cron", trigger_spec="0 9 * * *")
    │
    ▼
ScheduleManager.add_job()
    │  APScheduler 注册任务，写入 SQLite Schedule 表
    ▼
每天 09:00 触发
    │
    ▼
trigger_runner.py
    │  创建 virtual_conv_id（独立对话空间）
    │  调用 build_main_agent(conv_id=virtual_conv_id)
    │  执行原始 instruction
    ▼
执行完成
    │  写入 ScheduleNotification 表
    ▼
前端 NotificationBell 每 30 秒轮询 GET /notifications/unread
    └─ 显示红点 + 点击查看结果详情
```

### 5. 文件全文检索（FTS5）

```
用户上传文件 / 授权目录
    │
    ▼
file_index.py
    │  提取文本（PDF→pdfplumber, DOCX→python-docx...）
    │  写入 file_index_fts（SQLite FTS5 虚拟表）
    │  按段落切分 → 写入 chunk_index_fts
    ▼
用户搜索: "在我的论文里找 attention 相关段落"
    │
search_chunk_tool.run()
    │  FTS5 BM25 全文检索 → 返回 top-K 段落 + 文件路径
    ▼
MainAgent 综合结果回复用户
```

---

## 核心模块详解

### Agent 层（`agents/`）

**AgentBase**（`agents/base.py`）：所有 Agent 的基类，实现标准的 LLM 工具调用循环：
1. 构建包含历史 + 记忆的消息列表
2. 调用 LiteLLM streaming API
3. 解析 tool_use 响应 → 查找并执行工具
4. 将工具结果追加到消息列表，循环直到 stop_reason="end_turn"

**MainAgent**（`agents/main_agent.py`）：装备所有工具，唯一对用户直接负责的代理。

**SubAgentFactory**（`agents/sub/factory.py`）：按 `target` 名称（file/search/browser/computer/app）创建子代理，注入对应的工具子集和专属 prompt。

### SSE 事件协议（`protocol/events.py`）

前后端通过以下 SSE 事件类型通信：

| 事件 | 数据字段 | 含义 |
|------|---------|------|
| `thinking_delta` | `text` | 模型思考过程（extended thinking） |
| `content_delta` | `text` | 流式文字输出 |
| `tool_call_start` | `call_id, name, args` | 工具开始执行 |
| `tool_call_result` | `call_id, ok, preview, error` | 工具执行完成 |
| `card` | `type, payload` | 结构化卡片（文件列表/图片画廊/ask_user...） |
| `ask_user` | `ask_id, title, form_type, options` | 请求用户确认 |
| `sub_agent_start` | `agent_id, agent_name` | 子代理启动 |
| `sub_agent_end` | `agent_id, status` | 子代理完成 |
| `done` | — | 本次对话轮次结束 |
| `error` | `message` | 出错 |

### 安全层（`security/`）

**PathGuard**：拦截工具参数中的路径，禁止操作系统目录（`/System` `/Library` `/usr`）、敏感 dotfile（`~/.ssh` `~/.aws` `.env` `.gitconfig`）和 `../` 路径穿越。

**CmdGuard**：静态分析 shell 命令字符串，检测高危模式：`rm -rf` / `dd if=` / `mkfs` / 以及编码绕过（`base64 -d | sh` / `python -c` 中的 base64）。

**CredentialGuard**：在日志输出中自动检测并脱敏密钥前缀（`sk-` / `AKID` / `xoxb-` / `ghp_` / `AKIA`）。

### Skill 框架（`skill/`）

Skill 是带有受限工具白名单的"子代理模板"，以 YAML + Markdown 目录形式定义：

```
skills/builtins/file-organizer/
├── manifest.yaml      # 名称、版本、allowed_tools、参数声明
└── prompt.md          # skill 专属系统提示词
```

用户可在 `~/.openmarvis/skills/` 放置自定义 skill，系统启动时自动扫描注册。

---

## 与 Marvis 的对比与差异

Marvis 是一款优秀的商业 macOS AI 助手，OpenMarvis 以其行为规范为对标进行开源复现。以下是主要异同：

### 相同点

| 维度 | Marvis | OpenMarvis |
|------|--------|------------|
| 交互范式 | 对话驱动，一句话触发复杂任务 | ✅ 相同 |
| 架构思想 | Main Agent 路由 + Sub Agent 专项执行 | ✅ 相同 |
| 安全分级 | 🟢低/🟡中/🔴高三级风险 + ask_user 确认 | ✅ 相同 |
| 定时任务 | 自然语言设置定时 + GUI 管理 | ✅ 相同 |
| 文件能力 | 本地文件搜索/读写/分析 | ✅ 相同 |
| 网络搜索 | 联网检索 + 内容综合 | ✅ 相同 |
| 平台 | macOS 原生 | ✅ 相同 |

### 差异与改进方向

| 维度 | Marvis | OpenMarvis | 说明 |
|------|--------|------------|------|
| **开源性** | 闭源商业软件 | ✅ Apache 2.0 完全开源 | 可自部署、审计、二次开发 |
| **LLM 选择** | 绑定特定模型 | ✅ 任意 LLM（Claude/DeepSeek/混元/OpenAI 等） | 通过 LiteLLM 统一接入 |
| **数据隐私** | 数据经过 Marvis 服务器 | ✅ 完全本地运行，零数据上传 | 适合企业/敏感场景 |
| **Skill 扩展** | 固定内置能力 | ✅ 用户可自定义 Skill | 放 YAML+Prompt 即可扩展 |
| **Windows 支持** | ✅ 支持 Windows + Android 模拟器 | ⚠️ 仅 macOS（Windows 计划中） | 这是当前最大差距 |
| **Android 操控** | ✅ 可操控 Android 模拟器内的 App | ❌ 暂不支持 | 技术上可行，未实现 |
| **Vision 能力** | ✅ 屏幕截图 + 视觉理解指导操作 | 🔶 部分实现（app-agent 有 vision_backend） | 需进一步完善 |
| **GUI 配置** | ✅ 完整的图形化设置界面 | 🔶 基础设置页（Settings 页面） | 可继续补全 |
| **Timeline 可视化** | ✅ 详细执行过程展示 | ✅ 有 Timeline 面板（可折叠） | 功能相近 |
| **多模态输入** | ✅ 图片/截图直接粘贴 | 🔶 文件上传（含图片），未支持剪贴板粘贴 | 需添加 paste 事件处理 |
| **协作/多用户** | ❌ 单用户桌面工具 | ❌ 同为单用户（可改造） | — |

### 行为对齐状态

OpenMarvis 已完成多轮 Marvis 行为对齐（详见 `docs/superpowers/plans/`）：

- ✅ 极致克制的回复风格（零废话、零 emoji、禁止过程旁白）
- ✅ 三级风险分级与 ask_user 确认流程
- ✅ 专属确认工具豁免（delete 工具自带确认卡片，禁止双重询问）
- ✅ 编码绕过检测（CmdGuard）
- ✅ 全文检索 + 段落级检索（Marvis 的 search 能力对标）
- ✅ 定时任务自然语言设置
- ⚠️ Windows 兼容性（待实现）
- ⚠️ 剪贴板图片粘贴输入（待实现）

---

## 快速开始

### 前置依赖

```bash
# 系统工具
brew install python@3.11 node pnpm cliclick pandoc

# 可选（PDF 导出）
brew install --cask mactex-no-gui
```

### 安装与启动

以下命令请逐条执行：

```bash
git clone https://github.com/george351419-sys/OpenMarvis.git
cd OpenMarvis
make install
cd apps/backend
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key（三选一）：
# ANTHROPIC_API_KEY=sk-ant-...    （Claude，推荐）
# DEEPSEEK_API_KEY=sk-...          （DeepSeek，性价比高）
# HUNYUAN_API_KEY=...              （混元，国内首选）
cd ../..
make dev
```

打开 [http://localhost:3000](http://localhost:3000)

### 桌面客户端（可选）

```bash
cd apps/desktop
npm install
npm start        # 开发模式，直接打开桌面窗口
# npm run build:dmg  # 打包 .dmg 安装包
```

### 首次权限配置

macOS 需要授权：**系统设置 → 隐私与安全性**
- 辅助功能（app-agent 需要）
- 屏幕录制（vision_backend 截图需要）

---

## 能力一览

### 5 个 Sub Agent

| Agent | 负责领域 | 核心工具 |
|-------|---------|---------|
| `file-agent` | 本地文件全生命周期 | read_file / write_file / search_files_spotlight / search_chunk / convert_file |
| `search-agent` | 深度联网检索 + 综合 | web_search / web_fetch / ai_search |
| `browser-agent` | 人机交互式网页操作 | Playwright 全套（导航/点击/表单/截图） |
| `computer-agent` | macOS 系统级控制 | 音量/亮度/进程/剪贴板/系统设置 |
| `app-agent` | 第三方 App UI 自动化 | AX Accessibility API + Vision 视觉定位 |

### 6 个内置 Skill

| Skill | 触发场景 | 特点 |
|-------|---------|------|
| `file_organizer` | 整理混乱文件夹 | 先 list → 提案 → ask_user 确认 → 执行 |
| `document_writer` | 多源合成报告/摘要 | 支持 PDF/DOCX/MD 混合输入 |
| `excel_processing` | Excel/CSV 数据分析 | pandas 驱动，支持透视/过滤/合并 |
| `pdf` | PDF 拆分/合并/提取 | pdfplumber + pypdf |
| `document_convert` | 格式互转 | pandoc 后端，md↔docx↔pdf |
| `planning_with_files` | 长批量任务 | plan.json 断点续传，支持 50+ 文件批处理 |

### 30+ 内置工具

**文件读写**：`read_text` `read_file` `write_file` `edit_file` `delete` `list_dir` `convert_file` `send_file`

**搜索**：`search_files_spotlight`（macOS 原生）`search_file`（FTS5）`search_chunk`（段落级）`search_files`（os.walk）`search_image`

**网络**：`web_search` `web_fetch` `ai_search`

**执行**：`shell_executor` `python_executor`

**系统交互**：`ask_user` `dispatch_task` `present_result` `use_skill` `list_skills` `analyze_image`

**调度/偏好**：`create_schedule` `list_schedules` `cancel_schedule` `save_user_preference` `forget_user_preference`

---

## 安全模型

OpenMarvis 采用三层守护 + 三级风险的安全体系，确保 AI 不会在未经授权的情况下破坏用户数据。

### 三级风险

| 级别 | 场景示例 | 处理策略 |
|------|---------|---------|
| 🟢 低风险 | 读文件、搜索、创建新文件 | 直接执行，事后汇报 |
| 🟡 中风险 | 覆盖已有文件、修改配置、终止进程 | 告知影响后执行（用户主动要求时）或强制确认（AI 自主提议时） |
| 🔴 高风险 | 批量删除、清空目录、系统级写操作 | 必须弹出 ask_user 卡片，获得明确授权后方可执行 |

### 三条守护链

```
用户输入 → CmdGuard（命令检测）→ PathGuard（路径检测）→ 工具执行
                                                          ↓
                                               CredentialGuard（日志脱敏）
```

**PathGuard** 阻止：`/System` `/Library` `/usr` `/bin` `~/.ssh` `~/.aws` `.env` 及 `../` 跳转

**CmdGuard** 阻止：`rm -rf` `dd if=` `mkfs` `format` 以及 `base64 -d | sh` 等编码绕过攻击

**CredentialGuard** 脱敏：`sk-` `AKID` `xoxb-` `ghp_` `AKIA` 等密钥前缀

---

## 测试

```bash
cd apps/backend

# 单元测试 + 集成测试（336+ 用例）
.venv/bin/python -m pytest tests/ -v

# 类型检查（0 错误目标）
.venv/bin/python -m mypy openmarvis

# 代码风格
.venv/bin/python -m ruff check openmarvis
```

前端 E2E 测试（Playwright）：

```bash
cd apps/web
npx playwright test
```

CI 覆盖率门槛：85%。

---

## 路线图

| 版本 | 里程碑 | 状态 |
|------|--------|------|
| v0.1 | MVP：Main + File + Search Agent | ✅ 完成 |
| v0.5 | Browser / Computer / Spotlight 工具集 | ✅ 完成 |
| v1.0 | App Agent / Skill 框架 / 定时任务 / Timeline | ✅ 完成 |
| v1.1 | Marvis 行为对齐（风格/安全/工具） | ✅ 完成 |
| v1.2 | 6 内置 Skill + FTS5 段落检索 + UI 全面升级 | ✅ 当前 main |
| v1.3 | Windows 兼容 / 剪贴板图片粘贴 / 多模态增强 | 🚧 计划中 |
| v2.0 | 多用户 / 云端同步 / Skill 市场 | 💡 探索中 |

---

## 欢迎贡献

OpenMarvis 欢迎任何形式的贡献——无论是修复 Bug、添加新工具、编写 Skill、改进 UI，还是完善文档。

### 贡献方向

**🔧 扩展工具**
在 `apps/backend/openmarvis/tools/` 下新增 `my_tool.py`，继承 `Tool` 基类，实现 `run()` 方法，注册到 `MainAgent` 或目标 Sub Agent 即可。工具应声明 `risk_level`（low/medium/high）以接入安全门控。

**📦 编写自定义 Skill**
在 `~/.openmarvis/skills/my-skill/` 下放置：
```
my-skill/
├── manifest.yaml   # name, description, allowed_tools, params
└── prompt.md       # skill 执行指令（支持 {{param_name}} 占位符）
```
系统重启后自动加载，无需改动代码。

**🌐 Windows 兼容**
当前最大缺口。`computer/` 和 `app_automation/` 模块依赖 macOS 私有 API，需要对应的 Windows 实现（可参考 `pywinauto` / `uiautomation`）。

**🎨 前端改进**
`apps/web/components/` 中还有很多可以打磨的地方：深色模式适配、移动端响应式、Timeline 可视化增强、Markdown 渲染改进等。

**📝 文档与测试**
测试覆盖率还有提升空间，特别是 `browser/` 和 `app_automation/` 的集成测试。欢迎补充真实场景的测试用例。

### 提交规范

```bash
feat(scope): 新功能描述
fix(scope): Bug 修复描述
docs: 文档更新
test: 测试补充
refactor: 重构（不影响功能）
```

### 本地开发

以下命令请逐条执行：

```bash
# Fork 并克隆仓库
git checkout -b feat/my-feature

# 后端开发热重载
cd apps/backend
.venv/bin/uvicorn openmarvis.main:app --reload --port 8000

# 前端开发
cd apps/web
npm run dev
```

提交 PR 前请确保：
- `pytest tests/` 全部通过
- `mypy openmarvis` 无新增错误
- `ruff check openmarvis` 无警告

### 讨论与反馈

- **Issues**：Bug 报告和功能建议请开 GitHub Issue
- **Discussions**：架构讨论、使用问题、集成方案请用 Discussions
- **PR**：欢迎直接提 PR，会认真 Review

---

## License

Apache 2.0 — 详见 [LICENSE](LICENSE)。

可自由用于个人、商业、学术用途，修改后二次分发需保留原始版权声明。
