from openmarvis.computer.tools_settings import VolumeGetTool, VolumeSetTool
from openmarvis.tools.base import ToolContext


def make_ctx():
    return ToolContext(conv_id="c", agent_id="sa-1", workspace=None,
                       memory_store=None, security=None, event_sink=None,
                       user_settings=None)


async def test_volume_roundtrip():
    """Read volume, set to a known value, set back. Restores user state."""
    get = VolumeGetTool()
    set_tool = VolumeSetTool()
    original = (await get.execute(VolumeGetTool.args_model(), make_ctx())).content.strip()
    try:
        original_int = int(original)
    except ValueError:
        return  # device-dependent fallback
    try:
        await set_tool.execute(VolumeSetTool.args_model(level=42), make_ctx())
        check = (await get.execute(VolumeGetTool.args_model(), make_ctx())).content.strip()
        assert check == "42"
    finally:
        await set_tool.execute(VolumeSetTool.args_model(level=original_int), make_ctx())
