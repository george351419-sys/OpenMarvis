"""convert_file 工具：mock pandoc。"""
from __future__ import annotations

import pytest

from openmarvis.llm.event_sink import QueueEventSink
from openmarvis.security.policy import SecurityGate
from openmarvis.store.db import create_engine, init_db
from openmarvis.tools.base import ToolContext
from openmarvis.tools.convert_file import ConvertFileTool
from openmarvis.workspace.manager import Workspace


@pytest.fixture
def ctx(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    return ToolContext(
        conv_id="c", agent_id="main", workspace=ws,
        memory_store=None,
        security=SecurityGate(workspace=ws),
        event_sink=QueueEventSink(),
        user_settings=None,
    ), engine


async def test_pandoc_missing_returns_clear_error(ctx, monkeypatch):
    c, engine = ctx
    monkeypatch.setattr(
        "openmarvis.tools.convert_file._which", lambda _name: None,
    )
    f = c.workspace.output_dir / "a.md"
    f.write_text("# Hello")
    r = await ConvertFileTool(engine=engine).execute(
        ConvertFileTool.args_model(file_path=str(f), target_format="pdf"), c,
    )
    assert r.error is not None
    assert "pandoc" in r.error.lower()
    assert "brew install pandoc" in r.error


async def test_same_format_rejected(ctx, monkeypatch):
    c, engine = ctx
    monkeypatch.setattr(
        "openmarvis.tools.convert_file._which", lambda _name: "/fake/pandoc",
    )
    f = c.workspace.output_dir / "a.md"
    f.write_text("# Hello")
    r = await ConvertFileTool(engine=engine).execute(
        ConvertFileTool.args_model(file_path=str(f), target_format="md"), c,
    )
    assert r.error is not None
    assert "已是目标格式" in r.error


async def test_unsupported_ext_rejected(ctx, monkeypatch):
    c, engine = ctx
    monkeypatch.setattr(
        "openmarvis.tools.convert_file._which", lambda _name: "/fake/pandoc",
    )
    f = c.workspace.output_dir / "blob.xyz"
    f.write_bytes(b"\x00")
    r = await ConvertFileTool(engine=engine).execute(
        ConvertFileTool.args_model(file_path=str(f), target_format="pdf"), c,
    )
    assert r.error is not None
    assert ".xyz" in r.error


async def test_missing_source_rejected(ctx, monkeypatch):
    c, engine = ctx
    monkeypatch.setattr(
        "openmarvis.tools.convert_file._which", lambda _name: "/fake/pandoc",
    )
    r = await ConvertFileTool(engine=engine).execute(
        ConvertFileTool.args_model(
            file_path=str(c.workspace.output_dir / "ghost.md"),
            target_format="docx",
        ),
        c,
    )
    assert r.error is not None
    assert "不存在" in r.error


@pytest.mark.skipif(
    not __import__("shutil").which("pandoc"),
    reason="pandoc not installed; integration test skipped",
)
async def test_real_pandoc_md_to_html(ctx):
    """如果机器上真有 pandoc，跑一次端到端。"""
    c, engine = ctx
    f = c.workspace.output_dir / "hello.md"
    f.write_text("# Hello\n\nWorld\n")
    r = await ConvertFileTool(engine=engine).execute(
        ConvertFileTool.args_model(file_path=str(f), target_format="html"), c,
    )
    assert r.error is None
    out_path = c.workspace.output_dir / "hello.html"
    assert out_path.exists()
    body = out_path.read_text()
    assert "<h1" in body.lower()
    # mv-product 卡片
    assert r.cards and r.cards[0].type == "mv-product"


async def test_alias_source_path(ctx, monkeypatch):
    c, engine = ctx
    monkeypatch.setattr(
        "openmarvis.tools.convert_file._which", lambda _name: None,  # fail fast
    )
    args = ConvertFileTool.args_model.model_validate(
        {"source_path": "/nope/x.md", "target_format": "pdf"},
    )
    assert args.file_path == "/nope/x.md"
