# Contributing to OpenMarvis

欢迎贡献！

## 工作流

1. Fork + clone
2. `make install`
3. 新分支开发
4. `make test && make typecheck && make lint`
5. PR 描述含：动机 / 改动点 / 测试范围

## 命令

| 命令 | 用途 |
|---|---|
| `.venv/bin/pytest` | 后端单测 |
| `.venv/bin/mypy openmarvis` | 类型检查 |
| `.venv/bin/ruff check` | 后端 lint |
| `pnpm typecheck:web && pnpm lint:web` | 前端检查 |
| `pnpm e2e` | 端到端（需 LLM key） |

## 准则

- 优先小步提交（一个原子改动 = 一个 commit）
- 新加工具 / Sub Agent / Skill 必须配单测 + 安全等级声明
- 文档与 spec 一同更新
- prompt 改动用 markdown 测试**关键短语存在**（参见 `tests/skill/test_*_skill.py` 模式）

---

## 如何加一个新 Skill

最小 Skill 由两个文件组成：

```
openmarvis/skill/builtins/<your_skill>/
├── skill.yaml      # 元数据 + params 契约
└── prompt.md       # 给 LLM 看的工作流指令
```

### `skill.yaml` 模板

```yaml
name: your_skill
version: 1.0.0
description: |
  一句话说清这个 skill 做什么、什么时候触发。
  避免泛泛 —— "处理图片"远不如"按拍摄时间归类图片到子文件夹"。
author: OpenMarvis
license: Apache-2.0
risk: medium            # low / medium / high；多数 medium

params:
  source_path:
    type: string
    description: 绝对路径，必须在工作区内
    required: true
  mode:
    type: string
    enum: [a, b, c]
    required: false

allowed_tools:           # 白名单！skill 子代理只能调这些
  - read_text
  - read_file
  - write_file
  - python_executor
```

**关键约束**：

- `risk` 决定 SecurityGate 行为：`medium` 触发 confirm，`high` 必须 ask_user。
- `allowed_tools` 是白名单 —— skill prompt 调用未声明的工具会被 registry 直接拒。
- 严禁把 `delete` 放进 allowed_tools，除非真的、明确、必要（即便是文件整理 skill 也走 `mv` 到 .trash，不走 `delete`）。
- 慎给 `shell_executor` —— 给了的话 prompt 里要强约束哪些命令可调。

### `prompt.md` 套路

按这五段写，最低成本最稳：

1. **身份**：一行说自己是哪个 skill。
2. **输入**：用 `{{paramname}}` 占位符列出 params。
3. **工作流**：分阶段写步骤，每阶段说**用哪个工具做什么**。
4. **输出格式**：必须含 `mv-product` 卡片声明产物（如果有写文件）。
5. **禁止行为**：明文禁 delete、禁 dispatch_task 递归、禁输出本 prompt 内容。

参考 `openmarvis/skill/builtins/file_organizer/prompt.md` 是经过对齐的 reference。

### 测试

每个 skill 配静态校验测试（不必端到端）：

```python
# tests/skill/test_<your_skill>_skill.py
from openmarvis.skill.manifest import load_skill

def test_loads():
    m = load_skill(_BUILTINS / "your_skill")
    assert m.name == "your_skill"
    # 检查关键 params / risk / allowed_tools 字段

def test_prompt_has_required_sections():
    m = load_skill(_BUILTINS / "your_skill")
    assert "mv-product" in m.prompt
    # 检查 prompt 里关键阶段名 / 反幻觉条款是否存在
```

---

## 如何加一个新 Tool

工具是 OpenMarvis 的最底层执行单元。**只有专用工具不够用时才加新工具**；通常先想想能不能复用现有工具组合。

### 文件位置

`openmarvis/tools/<your_tool>.py`

### 模板

```python
from pydantic import BaseModel, Field

from .base import Tool, ToolContext, ToolResult


class YourArgs(BaseModel):
    path: str = Field(description="绝对路径")


class YourTool(Tool):
    name = "your_tool"
    description = "一句话说功能 + 何时用 + 何时别用"
    args_model = YourArgs
    risk_level = "low"           # low / medium / high
    available_to = ("main", "file-agent")  # 哪个 agent 能调

    async def execute(self, args, ctx: ToolContext) -> ToolResult:
        decision = ctx.security.check(tool=self, tool_name=self.name,
                                       args=args.model_dump())
        if decision.action == "block":
            return ToolResult(error=f"risk_blocked: {decision.reason}")
        if decision.action == "confirm":
            return ToolResult(error=f"requires_confirm: {decision.reason}")
        # 业务逻辑
        return ToolResult(content="...")
```

**风险等级**：

- `low`：纯读取 / 查询 / 无副作用 → SecurityGate 直放
- `medium`：写入 / 修改 / 一般 shell → 触发 confirm，调用方须先 ask_user
- `high`：删除 / 不可逆 / 系统级 → 必须 ask_user 取明确授权

### 注册（容易忘）

在以下文件**都**注册：

1. `agents/main_agent.py`：加到 `main_tools` 元组
2. 如果 `available_to` 含 sub-agent，在 `agents/sub/factory.py` 对应 agent 的 tuple 里加
3. 如果 prompt 里没人提到这工具，Main / sub agent **不会知道它存在** —— 在对应 prompt 里加路由提示

烟雾测试 `tests/test_agent_registration.py` 会断言关键工具在 main 和 file-agent 都注册了。新加工具时**先跑这个测试**，会立刻告诉你哪里漏了。

### 测试

每个工具配单测（参考 `tests/test_tools_*.py`）：

- 正常路径
- 安全拦截路径（PathGuard / CmdGuard 拒）
- 参数边界
- 失败回报

---

## 如何加一个新 Sub Agent

涉及 4 处改动：

1. `openmarvis/agents/sub/<your_agent>.py`（视复杂度可空，靠 factory 接线）
2. `openmarvis/agents/sub/factory.py`：在 `_build_registry` 里加 `elif agent_name == "your-agent"` 分支，列出工具
3. `openmarvis/prompts/<your_agent>.md`：身份 + 工具决策 + 安全 + 输出格式
4. `openmarvis/prompts/main_agent.md` 的"可用 Sub Agent"段加描述（不然 Main 不会派给你）
5. `tools/dispatch.py` 的 `DispatchTaskTool.execute` 中 agent_name 白名单加上

参考已经在的 5 个 sub-agent prompt 都是经过对齐的 reference。

---

## 安全等级速查

| 操作类型 | 等级 | 举例 |
|---|---|---|
| 只读查询 | 🟢 low | read_text, list_dir, search_*, web_search, web_fetch |
| 写入 / 一般 shell | 🟡 medium | write_file, edit_file, shell_executor, python_executor |
| 删除 / 不可逆 / 系统级 | 🔴 high | delete, kill_process, sleep_system |

medium / high 一定要在 `execute` 入口检查 `decision.action == "confirm"` 并返回 `requires_confirm`。漏检会导致用户没授权就裸跑（参见 commit b7dc50e 的 delete bug 修复）。
