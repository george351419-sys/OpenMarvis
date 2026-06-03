import pytest

from openmarvis.tools.dispatch import DispatchTaskArgs, DispatchTaskTool


def test_browser_agent_name_accepted():
    args = DispatchTaskTool.args_model(
        agent_name="browser-agent",
        task="<overall_goal>x</overall_goal><current_task>y</current_task>")
    assert args.agent_name == "browser-agent"


def test_computer_agent_name_accepted():
    args = DispatchTaskTool.args_model(
        agent_name="computer-agent",
        task="<overall_goal>x</overall_goal><current_task>y</current_task>")
    assert args.agent_name == "computer-agent"


@pytest.mark.asyncio
async def test_dispatch_accepts_app_agent_name():
    """Smoke test: 'app-agent' must not be rejected by the dispatch whitelist."""
    # Test that the whitelist check passes for app-agent by verifying
    # the DispatchTaskArgs model accepts it (args-level validation only)
    args = DispatchTaskArgs(
        agent_name="app-agent",
        task="<overall_goal>x</overall_goal><current_task>y</current_task>",
    )
    assert args.agent_name == "app-agent"
