import pytest

from openmarvis.security.policy import SecurityGate
from openmarvis.store.audit import writes_for_conv
from openmarvis.store.db import create_engine, init_db
from openmarvis.tools.base import ToolContext
from openmarvis.tools.fs import (
    DeleteTool,
    EditFileTool,
    ListDirTool,
    ReadTextTool,
    SearchFilesTool,
    WriteFileTool,
)
from openmarvis.workspace.manager import Workspace


@pytest.fixture
def ctx(tmp_path):
    ws = Workspace(conv_id="conv_a", root_base=tmp_path)
    ws.ensure()
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)

    class FakeSink:
        def __init__(self):
            self.events = []

        async def emit(self, name, data):
            self.events.append((name, data))

    return ToolContext(
        conv_id="conv_a",
        agent_id="main",
        workspace=ws,
        memory_store=None,
        security=SecurityGate(workspace=ws),
        event_sink=FakeSink(),
        user_settings=None,
    ), engine


async def test_write_then_read(ctx):
    c, engine = ctx
    target = c.workspace.output_dir / "x.md"
    await WriteFileTool(engine=engine).execute(
        WriteFileTool.args_model(file_path=str(target), content="hello"), c
    )
    r = await ReadTextTool().execute(ReadTextTool.args_model(file_path=str(target)), c)
    assert "hello" in r.content


async def test_write_accepts_path_alias(ctx):
    # Regression: 部分模型（Hunyuan-turbos）会用 "path" / "filepath" 而不是
    # "file_path"。args_model 应通过 validation_alias 接受这些别名，
    # 避免空转 4 次都失败。
    c, engine = ctx
    target = c.workspace.output_dir / "alias.md"
    # 用别名构造，model_validate 走 validation_alias 路径
    args = WriteFileTool.args_model.model_validate(
        {"path": str(target), "content": "from-alias"}
    )
    assert args.file_path == str(target)
    r = await WriteFileTool(engine=engine).execute(args, c)
    assert r.error is None
    assert target.read_text() == "from-alias"


async def test_write_records_audit(ctx):
    c, engine = ctx
    target = c.workspace.output_dir / "y.md"
    await WriteFileTool(engine=engine).execute(
        WriteFileTool.args_model(file_path=str(target), content="x"), c
    )
    rows = writes_for_conv(engine, "conv_a")
    assert any(r.path.endswith("y.md") for r in rows)


async def test_edit_replace_unique(ctx):
    c, engine = ctx
    target = c.workspace.output_dir / "z.md"
    target.write_text("foo bar")
    await EditFileTool().execute(
        EditFileTool.args_model(file_path=str(target), old_str="foo", new_str="baz"), c
    )
    assert target.read_text() == "baz bar"


async def test_edit_requires_unique_match(ctx):
    c, _ = ctx
    target = c.workspace.output_dir / "z.md"
    target.write_text("a a")
    r = await EditFileTool().execute(
        EditFileTool.args_model(file_path=str(target), old_str="a", new_str="b"), c
    )
    assert r.error is not None and "唯一" in r.error


async def test_list_dir(ctx):
    c, _ = ctx
    (c.workspace.output_dir / "a.txt").write_text("x")
    (c.workspace.output_dir / "b.txt").write_text("y")
    r = await ListDirTool().execute(
        ListDirTool.args_model(path=str(c.workspace.output_dir)), c
    )
    assert "a.txt" in r.content and "b.txt" in r.content


async def test_search_files(ctx):
    c, _ = ctx
    (c.workspace.output_dir / "alpha.md").write_text("hello")
    (c.workspace.output_dir / "beta.md").write_text("world")
    r = await SearchFilesTool().execute(
        SearchFilesTool.args_model(root=str(c.workspace.output_dir), name_glob="*.md"), c
    )
    assert "alpha.md" in r.content and "beta.md" in r.content


async def test_delete_moves_to_trash(ctx):
    c, _ = ctx
    target = c.workspace.output_dir / "del.md"
    target.write_text("bye")
    await DeleteTool().execute(DeleteTool.args_model(file_paths=[str(target)]), c)
    assert not target.exists()
