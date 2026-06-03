from __future__ import annotations

import logging
from typing import Any

import ulid

from ..agents.base import AgentBase, AgentResult
from ..tools.base import Tool
from ..tools.registry import ToolRegistry
from .manifest import SkillManifest

log = logging.getLogger(__name__)


class SkillToolRegistry(ToolRegistry):
    """ToolRegistry that ignores Tool.available_to and exposes all registered.

    Tools are already pre-filtered via allowed_tools at construction time.
    """

    def for_agent(self, agent_name: str) -> list[Tool]:                  # noqa: ARG002
        return list(self._tools.values())


def build_skill_registry(parent: ToolRegistry,
                          allowed: list[str]) -> SkillToolRegistry:
    """Filter parent registry by allowed-tools whitelist."""
    reg = SkillToolRegistry()
    missing: list[str] = []
    for name in allowed:
        t = parent.get(name)
        if t is None:
            missing.append(name)
            continue
        reg.register(t)
    if missing:
        log.warning("skill allowed_tools missing in parent registry: %s", missing)
    return reg


def render_skill_prompt(manifest: SkillManifest, params: dict[str, Any]) -> str:
    """Minimal placeholder render: replace {{params}} and {{<key>}}."""
    body = manifest.prompt
    body = body.replace("{{params}}", str(params))
    for k, v in params.items():
        body = body.replace("{{" + k + "}}", str(v))
    return body


async def run_skill(
    *,
    manifest: SkillManifest,
    params: dict[str, Any],
    parent_registry: ToolRegistry,
    llm,
    workspace,
    memory,
    security,
    event_sink,
    user_settings,
    conv_id: str,
) -> AgentResult:
    """Execute a Skill: build a filtered registry + AgentBase, run it."""
    validated = manifest.validate_params(params)
    registry = build_skill_registry(parent_registry, manifest.allowed_tools)
    agent = AgentBase(
        name=f"skill:{manifest.name}",
        agent_id=f"skill-{ulid.new().str.lower()}",
        conv_id=conv_id,
        system_prompt=render_skill_prompt(manifest, validated),
        llm=llm,
        tool_registry=registry,
        workspace=workspace,
        memory_store=memory,
        security=security,
        event_sink=event_sink,
        user_settings=user_settings,
        max_iterations=20,
    )
    await event_sink.emit("skill_loaded",
                            {"name": manifest.name, "version": manifest.version,
                             "params": validated, "agent_id": agent.agent_id})
    try:
        result = await agent.run(
            user_message=f"执行 skill '{manifest.name}'，参数: {validated}",
            memory_ids=[])
    finally:
        # 配对发 sub_agent_end，让前端 timeline 能闭合 skill 子节点。
        await event_sink.emit("sub_agent_end",
                                {"agent_id": agent.agent_id, "status": "ok"})
    return result
