from __future__ import annotations

from .base import Tool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("tool must have a non-empty name")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def for_agent(self, agent_name: str) -> list[Tool]:
        return [t for t in self._tools.values() if agent_name in t.available_to]

    def anthropic_schemas(self, agent_name: str) -> list[dict]:
        return [t.anthropic_schema() for t in self.for_agent(agent_name)]
