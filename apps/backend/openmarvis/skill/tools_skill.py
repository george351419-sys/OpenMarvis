from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from ..security.policy import RiskAssessment
from ..tools.base import Card, Tool, ToolContext, ToolResult
from ..tools.registry import ToolRegistry
from .registry import SkillRegistry
from .runner import run_skill


class UseSkillArgs(BaseModel):
    name: str = Field(description="已安装 Skill 的名字（来自 list_skills）")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="按 Skill manifest.params 提供的参数键值",
    )


class UseSkillTool(Tool):
    name = "use_skill"
    description = ("调起一个已注册的 Skill 工作流。Skill 在隔离子代理里运行，"
                   "只能调用 skill.yaml 声明的 allowed_tools。")
    args_model = UseSkillArgs
    available_to = ("main",)

    def __init__(self, *, skill_registry: SkillRegistry,
                 parent_tool_registry: ToolRegistry, llm):
        self.skills = skill_registry
        self.parent = parent_tool_registry
        self.llm = llm

    @property
    def risk_level(self) -> str:                  # noqa: D401  pragma: no cover
        return "low"

    def assess_risk(self, args: UseSkillArgs,
                     ctx: ToolContext | None) -> RiskAssessment:
        manifest = self.skills.get(args.name)
        if manifest is None:
            return RiskAssessment(level="low", reasons=[])
        return RiskAssessment(level=manifest.risk,
                                reasons=[f"skill {args.name} declared risk={manifest.risk}"])

    async def execute(self, args: UseSkillArgs, ctx: ToolContext) -> ToolResult:
        manifest = self.skills.get(args.name)
        if manifest is None:
            return ToolResult(error=f"未知 Skill: {args.name}")
        try:
            result = await run_skill(
                manifest=manifest, params=args.params,
                parent_registry=self.parent, llm=self.llm,
                workspace=ctx.workspace, memory=ctx.memory_store,
                security=ctx.security, event_sink=ctx.event_sink,
                user_settings=ctx.user_settings, conv_id=ctx.conv_id,
            )
        except ValueError as e:
            return ToolResult(error=str(e))
        card = Card(type="mv-skill-call",
                     payload=f"{manifest.name} → {result.status}")
        return ToolResult(content=result.final_content, cards=[card])


# ---------------- list_skills ----------------


class ListSkillsArgs(BaseModel):
    detail: bool = Field(
        default=False,
        description=(
            "False（默认）: 仅返回 [{name, description}, ...] 摘要。"
            "True: 加上 params 字段（每个 param 的 type / required / enum）。"
        ),
    )


class ListSkillsTool(Tool):
    name = "list_skills"
    description = (
        "枚举当前注册的所有 Skill（含 builtin 与用户 ~/.openmarvis/skills/ 下"
        "的自定义）。**不确定有哪个 skill 时先调本工具**，不要 hallucinate "
        "skill 名。"
    )
    args_model = ListSkillsArgs
    risk_level = "low"
    available_to = ("main",)

    def __init__(self, *, skill_registry: SkillRegistry):
        self.skills = skill_registry

    async def execute(self, args: ListSkillsArgs, ctx: ToolContext) -> ToolResult:
        manifests = self.skills.list()
        items: list[dict] = []
        for m in sorted(manifests, key=lambda x: x.name):
            entry: dict[str, Any] = {
                "name": m.name,
                "description": (m.description or "").strip(),
                "risk": m.risk,
            }
            if args.detail:
                entry["params"] = {
                    pname: {
                        "type": p.type,
                        "required": p.required,
                        "description": (p.description or "").strip(),
                        **({"enum": p.enum} if p.enum else {}),
                        **({"default": p.default} if p.default is not None else {}),
                    }
                    for pname, p in m.params.items()
                }
            items.append(entry)
        if not items:
            return ToolResult(content="（当前没有可见的 Skill）")
        # Markdown 表 给 LLM 看
        if args.detail:
            body = json.dumps(items, ensure_ascii=False, indent=2)
        else:
            lines = ["| skill | risk | 描述 |", "|---|---|---|"]
            for it in items:
                desc = it["description"].replace("\n", " ")[:200]
                lines.append(f"| `{it['name']}` | {it['risk']} | {desc} |")
            body = "\n".join(lines)
        return ToolResult(content=body)
