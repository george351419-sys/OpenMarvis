from openmarvis.security.policy import SecurityGate
from openmarvis.workspace.manager import Workspace


def test_gate_blocks_when_any_blocks(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    gate = SecurityGate(workspace=ws)
    d = gate.check(tool_name="shell_executor", args={"command": "rm -rf /"})
    assert d.action == "block"


def test_gate_confirm_when_path_outside(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    gate = SecurityGate(workspace=ws)
    d = gate.check(tool_name="write_file", args={"file_path": str(tmp_path / "out.txt"), "content": "x"})
    assert d.action == "confirm"


def test_gate_allows_inside_workspace(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    gate = SecurityGate(workspace=ws)
    d = gate.check(tool_name="write_file",
                   args={"file_path": str(ws.output_dir / "x.md"), "content": "hi"})
    assert d.action == "allow"
