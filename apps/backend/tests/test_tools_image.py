from PIL import Image

from openmarvis.security.policy import SecurityGate
from openmarvis.tools.base import ToolContext
from openmarvis.tools.image import AnalyzeImageTool, encode_image_b64
from openmarvis.workspace.manager import Workspace


def _make_image(path):
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    img.save(path)


def test_encode_image_b64_returns_data_url(tmp_path):
    p = tmp_path / "x.png"
    _make_image(p)
    s = encode_image_b64(str(p))
    assert s.startswith("data:image/")
    assert "base64," in s


async def test_max_10_images_limit(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()

    class Sink:
        async def emit(self, *a, **k):
            pass

    ctx = ToolContext(conv_id="c", agent_id="main", workspace=ws,
                      memory_store=None, security=SecurityGate(workspace=ws),
                      event_sink=Sink(), user_settings=None)
    paths = []
    for i in range(11):
        p = tmp_path / f"i{i}.png"
        _make_image(p)
        paths.append(str(p))
    tool = AnalyzeImageTool(llm=None)
    r = await tool.execute(AnalyzeImageTool.args_model(file_paths=paths, prompt="ignore"), ctx)
    assert r.error and "10" in r.error
