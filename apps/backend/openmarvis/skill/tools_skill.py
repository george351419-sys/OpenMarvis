from __future__ import annotations

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
