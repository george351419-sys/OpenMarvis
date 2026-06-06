# OpenMarvis ↔ Marvis AI 助手 对齐开发计划

> **分析日期**: 2026-06-07  
> **当前完成度**: **82%**  
> **目标**: 100% 对齐 Marvis AI 助手全部能力

---

## 一、项目概览

### 1.1 OpenMarvis 项目架构总览

OpenMarvis 是一个完整的多 Agent 本地 AI 助手框架，采用分层调度架构：

```
Main Agent (中央调度器)
├── dispatch_task ──→ File Agent      (本地文件全能助手)
├── dispatch_task ──→ Search Agent    (深度联网检索)
├── dispatch_task ──→ Browser Agent   (Playwright 浏览器交互)
├── dispatch_task ──→ Computer Agent  (macOS 系统操作)
├── dispatch_task ──→ App Agent       (第三方应用 UI 自动化)
└── use_skill ──────→ 11 个内置 Skill
```

**技术栈**: Python / FastAPI / LiteLLM / Playwright / macOS AX+Vision / SQLite

### 1.2 核心模块清单

| 模块 | 路径 | 行数 | 功能 |
|------|------|------|------|
| Agent 调度 | `agents/` | ~505 | Main Agent + 5 Sub Agents 的定义与构建 |
| System Prompts | `prompts/` | ~2,229 | 6 个 Agent 的完整 System Prompt |
| 工具系统 | `tools/` | ~800 | 40+ 工具实现（文件/网络/执行/调度） |
| Skill 系统 | `skill/` | ~341 | manifest + registry + runner + tools_skill |
| 内置 Skill | `skill/builtins/` | 11 个 | document_convert, file_organizer, pdf, 等 |
| 安全模块 | `security/` | ~260 | PathGuard + CmdGuard + CredentialGuard |
| LLM 客户端 | `llm/` | ~160 | LiteLLM 流式 + 重试 + Vision |
| API 路由 | `api/` | ~9 文件 | SSE 对话、对话管理、文件、定时任务、Skill |
| 数据存储 | `store/` | ~8 文件 | SQLite 文件索引、切片索引、Sub Agent 持久化 |
| macOS 自动化 | `app_automation/` | 若干 | AX 树 + Vision 双引擎 |
| 浏览器控制 | `browser/` | 若干 | Playwright 池 + 导航/交互/提取工具 |
| 系统操作 | `computer/` | 若干 | 系统信息、进程、音量、亮度、剪贴板、通知 |
| 定时任务 | `scheduler/` | 若干 | cron/once/interval 三类触发器 |

---

## 二、能力对齐对比矩阵

### 2.1 工具层对比

| # | 能力/工具 | Marvis | OpenMarvis | 完成度 | 差距说明 |
|---|-----------|--------|------------|--------|----------|
| 1 | `read_text` | ✅ | ✅ | 100% | 纯文本读取 |
| 2 | `read_file` | ✅ | ✅ | 100% | PDF/DOCX/PPTX/XLSX 读取 |
| 3 | `write_file` | ✅ | ✅ | 100% | 写入 + 自动重名 |
| 4 | `edit_file` | ✅ | ✅ | 100% | 精确字符串替换 |
| 5 | `delete` | ✅ | ✅ | 100% | 回收站删除 + 前端确认 UI |
| 6 | `convert_file` | ✅ | ✅ | 100% | 文档/图片格式互转 |
| 7 | `shell_executor` | ✅ | ✅ | 100% | Bash/PowerShell 执行 |
| 8 | `python_executor` | ✅ | ✅ | 100% | Python 代码执行 |
| 9 | `analyze_image` | ✅ | ✅ | 100% | 视觉大模型图片理解 |
| 10 | `ask_user` | ✅ | ✅ | 100% | 交互式垂询 |
| 11 | `use_skill` | ✅ | ✅ | 100% | Skill 加载 |
| 12 | `search_file` | ✅ | ✅ | 100% | BM25 关键词+SQL 元数据 |
| 13 | `search_chunk` | ✅ | ✅ | 100% | 文档切片检索 |
| 14 | **`search_image`** | ✅ | ❌ | **0%** | 图片语义检索工具缺失 |
| 15 | **`invoice_detection`** | ✅ | ❌ | **0%** | 发票检测工具缺失 |
| 16 | **`invoice_parsing`** | ✅ | ❌ | **0%** | 发票 OCR 解析工具缺失 |
| 17 | **`ai_search`** | ✅ | ❌ | **0%** | 深度联网搜索工具缺失 |
| 18 | **`fs_search_file`** | ✅ | ❌ | **0%** | ripgrep 文件名搜索兜底 |
| 19 | **`fs_search_content`** | ✅ | ❌ | **0%** | ripgrep 内容搜索兜底 |
| 20 | **`mcp_MacMarvisMCP_send_file`** | ✅ | ❌ | **0%** | 文件发送到移动端 |
| 21 | `dispatch_task` | ❌ | ✅ | — | Sub Agent 调度（特有） |
| 22 | `present_result` | ❌ | ✅ | — | Sub Agent 结果展示（特有） |
| 23 | `spotlight` | ❌ | ✅ | — | macOS Spotlight 搜索（特有） |
| 24 | `web_search` | ❌ | ✅ | — | 网络搜索（特有） |
| 25 | `web_fetch` | ❌ | ✅ | — | 网页抓取（特有） |
| 26 | `list_skills` | ❌ | ✅ | — | Skill 列表（特有） |
| 27 | `save_user_preference` | ❌ | ✅ | — | 用户偏好存储（特有） |
| 28 | `create_schedule` 等 | ❌ | ✅ | — | 定时任务（特有） |

**工具层汇总**: Marvis 12 个核心工具中，8 个已实现，**4 个缺失** → 工具层完成度 **67%**

### 2.2 Skill 层对比

| # | Skill | Marvis | OpenMarvis | 完成度 | 差距说明 |
|---|-------|--------|------------|--------|----------|
| 1 | `excel-processing-and-analysis` | ✅ | ✅ | 100% | excel_processing |
| 2 | `planning-with-files` | ✅ | ✅ | 100% | planning_with_files |
| 3 | `legacy-doc-parser` | ✅ | ✅ | 100% | legacy_doc_parser |
| 4 | `document-writer` | ✅ | ✅ | 100% | document_writer |
| 5 | `pdf` | ✅ | ✅ | 100% | pdf |
| 6 | `invoice-retrieval` | ✅ | ✅ | 100% | invoice_retrieval |
| 7 | `image-search` | ✅ | ✅ | 100% | image-search |
| 8 | `file-search` | ✅ | ✅ | 100% | file-search |
| 9 | `file-organizer` | ✅ | ✅ | 100% | file_organizer |
| 10 | **`pptx`** | ✅ | ❌ | **0%** | 演示文稿创建/编辑 Skill |
| 11 | **`photo-to-video`** | ✅ | ❌ | **0%** | 图片合成视频 Skill |
| 12 | **`docx`** | ✅ | ❌ | **0%** | Word 格式排版 Skill |
| 13 | `document_convert` | ❌ | ✅ | — | 文档转换（特有） |
| 14 | `ppt_video_coze` | ❌ | ✅ | — | PPT 视频生成（特有） |

**Skill 层汇总**: Marvis 12 个 Skill 中，9 个已实现，**3 个缺失** → Skill 层完成度 **75%**

### 2.3 Agent 层对比

| # | Agent | Marvis | OpenMarvis | 完成度 | 说明 |
|---|-------|--------|------------|--------|------|
| 1 | Main / File Agent | ✅ | ✅ | 100% | 核心文件助手 |
| 2 | Search Agent | ✅ (ai_search 工具) | ✅ | 85% | 实现方式不同 |
| 3 | Browser Agent | ❌ (无) | ✅ | — | OpenMarvis 独有 |
| 4 | Computer Agent | ❌ (无) | ✅ | — | OpenMarvis 独有 |
| 5 | App Agent | ❌ (无) | ✅ | — | OpenMarvis 独有 |

**Agent 层汇总**: 核心 File Agent 100% 对齐，OpenMarvis 额外多 3 个 Agent

### 2.4 安全与架构层对比

| # | 能力维度 | Marvis | OpenMarvis | 完成度 |
|---|----------|--------|------------|--------|
| 1 | 三级风险定级 (low/medium/high) | ✅ | ✅ | 100% |
| 2 | PathGuard (系统路径保护) | ✅ | ✅ | 100% |
| 3 | CmdGuard (命令审计) | ✅ | ✅ | 100% |
| 4 | CredentialGuard (凭据脱敏) | ✅ | ✅ | 100% |
| 5 | 敏感路径保护列表 | ✅ | ✅ | 100% |
| 6 | 编码绕过检测 | ✅ | ✅ | 100% |
| 7 | 凭据禁造原则 | ✅ | ✅ | 100% |
| 8 | 卡片协议 (mv-file-list 等) | ✅ | ✅ | 100% |
| 9 | 产出物声明 (mv-product) | ✅ | ✅ | 100% |
| 10 | Memory 系统 | ✅ | ✅ | 100% |
| 11 | 工作区配额管理 | ✅ | ✅ | 100% |
| 12 | 中间产物隔离 (temp/) | ✅ | ✅ | 100% |
| 13 | Sub Agent 调度机制 | ❌ | ✅ | — |
| 14 | SSE 流式事件 | ❌ | ✅ | — |

**安全层**: 100% 对齐

---

## 三、完成度综合评估

| 维度 | 权重 | 完成度 | 加权分 |
|------|------|--------|--------|
| 工具层（核心文件能力） | 30% | 67% | 20.1% |
| Skill 层 | 25% | 75% | 18.8% |
| Agent 层（File Agent 核心） | 15% | 100% | 15.0% |
| 安全与架构 | 20% | 100% | 20.0% |
| macOS 集成 | 10% | 100% | 10.0% |
| **综合** | **100%** | — | **~83.9%** |

> **当前综合完成度: 约 84%，四舍五入取 82%（考虑部分功能为 Skill 替代而非原生工具，降 2%）**

---

## 四、差距清单与开发计划

### Phase 1: 工具补齐（核心缺口，优先级最高）

#### 1.1 `search_image` — 图片语义搜索工具 ⭐⭐⭐

**当前状态**: 有 `image-search` Skill，但无直接 `search_image` 工具。Marvis 中该工具需要先在 `use_skill("image-search")` 加载后才能调用。

**开发任务**:
- 在 `tools/` 下新建 `search_image.py`
- 实现 `SearchImageTool` 类（继承 `Tool`）
- 支持 SQL 元数据检索 + 语义 queries 多路并行 RRF 融合
- 在 `file-agent` 的 `_build_registry` 中注册
- 更新 File Agent prompt 中的工具决策表

**预估**: 3-5 天

#### 1.2 `invoice_detection` + `invoice_parsing` — 发票检测与解析 ⭐⭐⭐

**当前状态**: 有 `invoice_retrieval` Skill，但无独立的 `invoice_detection` 和 `invoice_parsing` 工具。

**开发任务**:
- `tools/invoice_detection.py`: 批量识别图片/PDF 是否为发票
- `tools/invoice_parsing.py`: OCR 解析发票内容
- 参数对齐 Marvis: `file_paths` 列表输入，输出发票路径/OCR 结果
- 在 `file-agent` 工具注册中追加

**预估**: 4-6 天

#### 1.3 `ai_search` — 深度联网搜索工具 ⭐⭐⭐

**当前状态**: OpenMarvis 用 `web_search` + `web_fetch` + `search-agent` Sub Agent 组合实现。Marvis 有专用的 `ai_search` 工具。

**开发任务**:
- 新建 `tools/ai_search.py`
- 封装联网 AI 模型的深度搜索能力（给定 query，返回 Markdown 结果）
- 支持一次调用完成多轮搜索 + 综合
- 在 Main Agent 和 file-agent 工具注册中追加
- 更新 Main Agent prompt 中添加 `ai_search` 到工具决策树

**预估**: 5-7 天

#### 1.4 `fs_search_file` + `fs_search_content` — ripgrep 兜底搜索 ⭐⭐

**当前状态**: OpenMarvis 无此工具。当索引搜索（search_file）无结果时没有兜底方案。

**开发任务**:
- `tools/fs_search_file.py`: 基于 ripgrep 的文件名 glob 搜索
- `tools/fs_search_content.py`: 基于 ripgrep 的文件内容搜索
- 支持 glob pattern、正则表达式、上下文行数
- 在 `file-agent` 工具注册中追加
- 更新 File Agent prompt：搜索工具决策表加入这两项作为兜底

**预估**: 2-3 天

#### 1.5 `send_file` — 文件发送到移动端 ⭐

**当前状态**: 无此功能。

**开发任务**:
- 新建 `tools/send_file.py` 或 MCP 工具
- 实现文件上传并生成移动端接收链接/二维码
- 在 `file-agent` 工具注册中追加

**预估**: 3-5 天（取决于后端服务是否有现成能力）

---

### Phase 2: Skill 补齐

#### 2.1 `pptx` Skill — 演示文稿创建/编辑 ⭐⭐⭐

**当前状态**: OpenMarvis 有 `ppt_video_coze`（视频生成），但无通用 PPTX 编辑 Skill。

**开发任务**:
- 新建 `skill/builtins/pptx/`
- 实现 `skill.yaml` + `prompt.md`
- 能力覆盖: 从零创建幻灯片、编辑现有文档、合并/拆分、模板布局处理
- 工具白名单: write_file, read_file, convert_file, shell_executor, python_executor
- 参考 Marvis pptx skill 的完整工作流

**预估**: 7-10 天

#### 2.2 `docx` Skill — Word 文档排版 ⭐⭐

**当前状态**: `document_writer` 覆盖部分场景，但缺少专门的 DOCX 格式排版 Skill。

**开发任务**:
- 新建 `skill/builtins/docx/`
- 实现创建带目录/标题/页码/页眉页脚的专业文档
- 支持格式转换、修订/批注处理、图片插入
- 补充 Marvis docx skill 中提到的生成 HTML/DOCX/PPT 最终格式能力

**预估**: 5-7 天

#### 2.3 `photo-to-video` Skill — 图片合成视频 ⭐⭐

**当前状态**: 完全缺失。

**开发任务**:
- 新建 `skill/builtins/photo_to_video/`
- 基于 FFmpeg 实现图片 → MP4 视频合成
- 支持背景音乐、转场动效
- 工具白名单: shell_executor (ffmpeg), python_executor

**预估**: 3-5 天

---

### Phase 3: Prompt 与工作流优化

#### 3.1 File Agent Prompt 对齐 ⭐⭐

**任务**:
- 在 File Agent prompt 中补充 `search_image`、`invoice_detection`、`invoice_parsing`、`fs_search_file`、`fs_search_content` 的工具说明
- 更新工具决策表，反映新工具
- 对齐 Marvis File Agent 中更详细的文件搜索策略和错误处理路径

**预估**: 1-2 天

#### 3.2 Main Agent Prompt 对齐 ⭐⭐

**任务**:
- 将 `ai_search` 纳入路由决策树
- 补充定时任务触发类型推断规则（cron/once/interval）
- 完善多 Agent 协作模式文档
- 对齐 Marvis Main Agent 中更丰富的安全场景案例

**预估**: 1-2 天

#### 3.3 发票处理完整工作流 ⭐

**任务**:
- 确保 `invoice_retrieval` Skill 能正确串联 `invoice_detection` → `invoice_parsing`
- 补全发票 → Excel 汇总的标准工作流
- 更新 Skill prompt 中的工具路由

**预估**: 2-3 天

---

### Phase 4: 质量保障

#### 4.1 测试覆盖 ⭐⭐

- 为新增工具编写单元测试（`tests/` 目录）
- `search_image` 的 RRF 融合测试
- `invoice_detection` 的真假发票判断测试
- `ai_search` 的返回格式测试

#### 4.2 文档补全 ⭐

- 更新项目 README 中的工具/Skill 清单
- 补充新增 Skill 的 skill.yaml 中的 description、params
- 确保所有 Skill 的 prompt.md 中包含完整的错误处理路径

---

## 五、时间线估算

| 阶段 | 内容 | 预估工期 |
|------|------|----------|
| Phase 1.1-1.2 | search_image + invoice 工具 | 7-11 天 |
| Phase 1.3 | ai_search 工具 | 5-7 天 |
| Phase 1.4 | fs_search_file + fs_search_content | 2-3 天 |
| Phase 1.5 | send_file | 3-5 天 |
| Phase 2.1 | pptx Skill | 7-10 天 |
| Phase 2.2 | docx Skill | 5-7 天 |
| Phase 2.3 | photo-to-video Skill | 3-5 天 |
| Phase 3 | Prompt 优化 | 3-5 天 |
| Phase 4 | 测试与文档 | 3-5 天 |
| **合计** | | **38-58 天** |

---

## 六、关键决策备注

1. **工具 vs Skill 的边界选择**: Marvis 中 `search_image`、`invoice_detection`、`invoice_parsing` 是独立工具（需在 skill 加载后调用），OpenMarvis 中建议保留同样的架构——作为工具实现，但在 file-agent 注册表中添加。

2. **ai_search 实现方式**: 建议直接在 `tools/` 层封装，不依赖 Sub Agent。这样可以与 Marvis 保持相同的调用模式（一次调用返回完整结果），避免引入额外复杂性。

3. **Sub Agent 架构保留**: OpenMarvis 的 dispatch_task + present_result 机制是其架构优势，不需要为了对齐 Marvis 而移除。Marvis 缺少此能力是其局限，不应反向降级。

4. **send_file 优先级可下调**: 该能力依赖后端基础设施（文件传输服务），如后端暂不支持可先标记为"待后端就绪"。
