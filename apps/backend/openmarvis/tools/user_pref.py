from __future__ import annotations

from pydantic import BaseModel, Field

from ..memory.store import USER_PREF_CONV_ID
from .base import Tool, ToolContext, ToolResult


class SaveUserPreferenceArgs(BaseModel):
    rule: str = Field(
        description="一句话偏好规则，第一人称用户视角。例：'不要用 emoji'、'文件总写到 ~/Desktop'、'回复用英文'。"
    )


class SaveUserPreferenceTool(Tool):
    name = "save_user_preference"
    description = (
        "保存用户的长期偏好规则（跨会话生效）。仅在用户**明确**表达通用偏好时调用——"
        "如'以后都...'、'别再...'、'记住我喜欢...'。一次性请求不要存。"
    )
    args_model = SaveUserPreferenceArgs
    risk_level = "low"
    available_to = ("main",)

    async def execute(self, args: SaveUserPreferenceArgs, ctx: ToolContext) -> ToolResult:
        if ctx.memory_store is None:
            return ToolResult(error="memory_store_unavailable")
        rule = args.rule.strip()
        if not rule:
            return ToolResult(error="rule_empty")
        if len(rule) > 500:
            return ToolResult(error="rule_too_long: 偏好规则单条 ≤ 500 字符；请精简或拆条。")
        pref_id = await ctx.memory_store.put(
            conv_id=USER_PREF_CONV_ID, content=rule, kind="user_pref",
        )
        return ToolResult(content=f"已记住偏好（{pref_id}）：{rule}")


class ForgetUserPreferenceArgs(BaseModel):
    pref_id: str = Field(description="要删除的偏好 id（memory_xxx）")


class ForgetUserPreferenceTool(Tool):
    name = "forget_user_preference"
    description = "删除一条已保存的用户偏好。用户说'忘了那条'/'撤销刚才的偏好'时调用。"
    args_model = ForgetUserPreferenceArgs
    risk_level = "low"
    available_to = ("main",)

    async def execute(self, args: ForgetUserPreferenceArgs, ctx: ToolContext) -> ToolResult:
        if ctx.memory_store is None:
            return ToolResult(error="memory_store_unavailable")
        ok = await ctx.memory_store.delete_user_pref(pref_id=args.pref_id)
        if not ok:
            return ToolResult(error=f"pref_not_found: {args.pref_id}")
        return ToolResult(content=f"已删除偏好 {args.pref_id}")
