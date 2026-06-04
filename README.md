# OpenMarvis

> 开源 Marvis-like 桌面智能体 · macOS · Apache 2.0

OpenMarvis 是开源、可扩展的桌面 AI 助手框架，采用 **Main Agent → Sub Agent → Skill → Tool** 四级降级调度。

## 状态

- **v1.0.x（开发中）**：5 个 Sub Agent + 6 个内置 Skill + FTS5 文件索引 + 定时任务 + Timeline
- **平台**：macOS 14+（Windows 在计划中）
- **后端**：Python 3.11 + FastAPI + Pydantic + LiteLLM + Playwright + APScheduler + SQLite/FTS5
- **前端**：Next.js 14 + Tailwind + shadcn/ui + Zustand

## 能力一览

### 5 个 Sub Agent

| Agent | 干什么 |
|---|---|
| `file-agent` | 本地文件：搜索 / 读写 / 分析 / 改格式 / 批量整理（含 Spotlight + FTS5 索引） |
| `search-agent` | 深度联网检索 + LLM 综合（不必用于简单事实） |
| `browser-agent` | 必须人机交互的网页操作（登录 / 表单 / 多页跳转，Playwright） |
| `computer-agent` | macOS 系统级：进程 / 自带 app / 设置 / 音量亮度 / 剪贴板 / 锁屏 |
| `app-agent` | 第三方应用 UI 自动化（AX + Vision 双引擎） |

### 6 个内置 Skill

| Skill | 触发场景 |
|---|---|
| `document_convert` | md ↔ docx ↔ pdf（pandoc 后端） |
| `file_organizer` | 整理 Downloads / 把这堆文件分类（扫 → 提案 → ask_user → 执行） |
| `pdf` | PDF 抽文本 / 拆分 / 合并 |
| `document_writer` | 多份源 → 报告 / 摘要 / 对比 / 提案 |
| `excel_processing` | Excel/CSV 探查 / 过滤 / 透视 / 合并（pandas） |
| `planning_with_files` | 长批量任务带 plan.json 断点续传 |

调 `list_skills` 让 Main Agent 自查；用户在 `~/.openmarvis/skills/` 放自定义 skill 会被自动扫到。

### 22+ 内置工具

**文件**：`read_text` / `read_file` (PDF/DOCX/PPTX/XLSX/CSV) / `write_file` / `edit_file` (CRLF-safe) / `delete` / `list_dir` / `convert_file`

**搜索**：`search_files_spotlight` (macOS 原生) / `search_file` (FTS5 BM25) / `search_chunk` (段落级 FTS5) / `search_files` (os.walk)

**网络**：`web_search` / `web_fetch`

**系统/任务**：`shell_executor` / `python_executor` / `ask_user` / `dispatch_task` / `present_result` / `use_skill` / `list_skills` / `analyze_image`

**定时/偏好**：`create_schedule` / `list_schedules` / `cancel_schedule` / `save_user_preference` / `forget_user_preference`

### 安全模型

三级风险（🟢 直接 / 🟡 二次确认 / 🔴 必确认）+ 三条守护链：

- **PathGuard**：系统级保护（`/System` `/Library` `/usr`...）+ 敏感目录（`~/.ssh` `~/.aws` `.env`...）+ `../` 跳转解析输出真实路径
- **CmdGuard**：高危命令模式 + **编码绕过检测**（`base64 -d` / `echo $(...) | sh` / `python -c base64...` / `eval $(...)`）
- **CredentialGuard**：日志中密钥前缀（`sk-` / `AKID` / `xoxb-`）自动脱敏

## 快速开始

前置：Python 3.11、Node 20、pnpm 9。

```bash
git clone <repo> openmarvis && cd openmarvis
make install
cd apps/backend && cp .env.example .env
# 把 .env 里的 HUNYUAN_API_KEY 改成你的（混元、DeepSeek、Claude 任选一家，改 config 即可）
cd ../.. && make dev
```

打开 http://localhost:3000。

### 推荐的系统依赖

```bash
brew install python@3.11      # 后端 runtime（venv 用）
brew install cliclick         # app-agent vision_click 的鼠标驱动
brew install pandoc           # document_convert / convert_file
brew install --cask mactex-no-gui  # 可选，要导出 PDF 时用
```

首次运行会请求 macOS **辅助功能** 与 **屏幕录制** 权限：
"系统设置 → 隐私与安全性" 里勾选 OpenMarvis（或运行它的终端 / Python）。

## 试一试

### 文件 / 文档

```
# 读复杂文档
"~/Desktop/合同.pdf 里关于违约责任的条款是什么？"

# 段落级搜索（长文档定位）
"在我的论文目录里找提到 self-attention 的段落"

# 整理目录
"帮我把 ~/Downloads 按类型整理（先演练）"

# 多源合成
"把这三份季报合成一份对比报告：[a.pdf] [b.pdf] [c.pdf]"

# Excel 透视
"~/Desktop/sales.xlsx 按产品分组求和"

# PDF 拆分
"把 ~/Desktop/book.pdf 拆成单页 PDF"
```

### 网络 / 系统 / 应用

```
# 网搜（自动选 web_search vs search-agent）
"对比一下 Claude 4 / GPT-5 / Gemini 3 在长上下文的表现"

# macOS 系统
"我的内存还剩多少？" / "调音量到 30%" / "杀掉占 CPU 最多的进程"

# 第三方 app
"在微信发消息给妈妈：晚饭吃过了"

# 浏览器
"打开 GitHub 我的通知页面，看看有没有 @ 我"
```

### 定时任务 + 偏好

```
"每天早上 9 点给我发一条北京天气"
"以后回复都别用 emoji。因为我用纯文本笔记。"   ← 会持久化到 ~/.openmarvis
```

### 长批量任务（断点续传）

```
"用 planning_with_files 把 ~/Downloads/papers 下的 50 篇 PDF 各自总结成 1 页摘要"
# plan.json 写到 temp/，中途任何时候可以重新调用 skill resume
```

## UI 入口

- ✨ Skills — 内置 + 用户自定义清单
- 🕒 定时任务 — 列出 / 取消
- 🔔 通知 — 定时任务执行结果
- 右栏 **Timeline** — agent / tool-call 实时轨迹（含越级警告、卡片渲染）

## 文档

- 架构 spec：`docs/superpowers/specs/2026-06-01-openmarvis-design.md`
- Marvis 对齐分析（多份）：`docs/superpowers/plans/`
- 测试指南：[`docs/TESTING.md`](docs/TESTING.md)
- 贡献指南：`CONTRIBUTING.md`

## 测试

```bash
cd apps/backend
.venv/bin/python -m pytest tests/   # 336+ tests
.venv/bin/python -m mypy openmarvis # 0 errors / 97 files
```

CI 跑 ruff + mypy + pytest + 覆盖率 85% 门槛。

## 路线图状态

| 版本 | 里程碑 | 状态 |
|---|---|---|
| v0.1 | MVP（Main + File + Search Agent）| ✅ |
| v0.5 | + Browser / Computer / Spotlight | ✅ |
| v1.0 | + App Agent / Skill / Scheduler / Timeline | ✅ 主体完成 |
| v1.1 | Marvis 行为对齐（10 轮 commit）| ✅（当前 main） |
| v1.2 | 6 内置 skill + FTS5 索引 + Sub agent prompt 全扩 | ✅（当前 main） |
| 未来 | Windows 兼容 / 更多 skill / Timeline 增强 | — |

## License

Apache 2.0 — 详见 LICENSE。
