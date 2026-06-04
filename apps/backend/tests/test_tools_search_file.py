"""search_file 工具 + FTS5 索引：索引建立、增量、查询、ranking。"""
from __future__ import annotations

import pytest

from openmarvis.llm.event_sink import QueueEventSink
from openmarvis.security.policy import SecurityGate
from openmarvis.store.db import create_engine, init_db
from openmarvis.store.file_index import (
    FileIndexHit,
    index_directory,
    index_path,
    prune_missing,
    search,
    stats,
)
from openmarvis.tools.base import ToolContext
from openmarvis.tools.search_file import SearchFileTool
from openmarvis.workspace.manager import Workspace


@pytest.fixture
def ctx(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    return (ToolContext(
        conv_id="c", agent_id="main", workspace=ws,
        memory_store=None,
        security=SecurityGate(workspace=ws),
        event_sink=QueueEventSink(),
        user_settings=None,
    ), engine)


# ---------------- store/file_index.py 单元 ----------------


def test_index_single_file_and_search(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    f = tmp_path / "doc.md"
    f.write_text("hello world\nthis is about pandas\n")
    assert index_path(engine, conv_id="c", path=f) is True
    hits = search(engine, conv_id="c", query="pandas")
    assert len(hits) == 1
    assert hits[0].path == str(f)
    assert "pandas" in hits[0].snippet.lower()


def test_index_incremental_skips_unchanged(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    f = tmp_path / "x.txt"
    f.write_text("first")
    assert index_path(engine, conv_id="c", path=f) is True
    # 不改文件再索引 → 跳过
    assert index_path(engine, conv_id="c", path=f) is False


def test_index_directory_recursive(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.md").write_text("alpha keyword")
    (tmp_path / "sub" / "b.md").write_text("beta keyword")
    (tmp_path / "ignored.bin").write_bytes(b"\x00\x01")
    stats_dict = index_directory(engine, conv_id="c", root=tmp_path)
    # a.md + b.md + ignored.bin（即便 .bin 也会被索引到 path/name）
    assert stats_dict["indexed"] >= 2
    hits = search(engine, conv_id="c", query="keyword")
    assert len(hits) == 2


def test_search_per_conv_isolation(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    f1 = tmp_path / "f1.md"
    f1.write_text("apple in conv_a")
    f2 = tmp_path / "f2.md"
    f2.write_text("apple in conv_b")
    index_path(engine, conv_id="conv_a", path=f1)
    index_path(engine, conv_id="conv_b", path=f2)
    hits_a = search(engine, conv_id="conv_a", query="apple")
    hits_b = search(engine, conv_id="conv_b", query="apple")
    assert len(hits_a) == 1 and len(hits_b) == 1
    assert hits_a[0].path == str(f1)
    assert hits_b[0].path == str(f2)


def test_search_by_name_field(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    f = tmp_path / "weekly-report.md"
    f.write_text("内容里没有这个词")
    index_path(engine, conv_id="c", path=f)
    hits = search(engine, conv_id="c", query="weekly", field="name")
    assert len(hits) == 1


def test_prune_missing_files(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    f = tmp_path / "gone.md"
    f.write_text("content")
    index_path(engine, conv_id="c", path=f)
    f.unlink()
    removed = prune_missing(engine, conv_id="c")
    assert removed == 1
    assert stats(engine, conv_id="c")["file_count"] == 0


# ---------------- SearchFileTool ----------------


async def test_tool_with_reindex_root(ctx):
    c, engine = ctx
    (c.workspace.output_dir / "alpha.md").write_text("python is great")
    (c.workspace.output_dir / "beta.md").write_text("rust is great too")
    tool = SearchFileTool(engine=engine)
    r = await tool.execute(
        SearchFileTool.args_model(query="python",
                                    reindex_root=str(c.workspace.output_dir)),
        c,
    )
    assert r.error is None
    assert "alpha.md" in r.content
    assert "beta.md" not in r.content


async def test_tool_returns_card_when_hits(ctx):
    c, engine = ctx
    (c.workspace.output_dir / "x.md").write_text("找到这个关键词")
    tool = SearchFileTool(engine=engine)
    r = await tool.execute(
        SearchFileTool.args_model(query="关键词",
                                    reindex_root=str(c.workspace.output_dir)),
        c,
    )
    assert r.cards and r.cards[0].type == "mv-file-list"


async def test_tool_no_hits(ctx):
    c, engine = ctx
    tool = SearchFileTool(engine=engine)
    r = await tool.execute(
        SearchFileTool.args_model(query="impossible_xyz_zzz"), c,
    )
    assert r.error is None
    assert "未找到" in r.content
