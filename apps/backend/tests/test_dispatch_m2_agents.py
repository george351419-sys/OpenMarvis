from openmarvis.tools.dispatch import DispatchTaskTool


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
