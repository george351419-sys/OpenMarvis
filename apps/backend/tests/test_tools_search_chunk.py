"""chunk_index store + search_chunk tool。"""
from __future__ import annotations

import pytest

from openmarvis.llm.event_sink import QueueEventSink
from openmarvis.security.policy import SecurityGate
from openmarvis.store.chunk_index import (
    chunk_stats,
    chunk_text,
    index_directory_chunks,
    index_path_chunks,
    search_chunks,
)
from openmarvis.store.db import create_engine, init_db
from openmarvis.tools.base import ToolContext
from openmarvis.tools.search_chunk import SearchChunkTool
from openmarvis.workspace.manager import Workspace


# ---------------- chunker 单元 ----------------


def test_chunker_short_text_one_chunk():
    chunks = chunk_text("hello world")
    assert chunks == ["hello world"]


def test_chunker_splits_long_paragraphs():
    p1 = "a" * 500
    p2 = "b" * 500
    p3 = "c" * 500
    raw = "\n\n".join([p1, p2, p3])
    # 默认 target=1200，所有三个 ≈1500 应该切成两块
    chunks = chunk_text(raw, target_chars=800)
    assert len(chunks) >= 2
    # 每个 chunk 完整保留对应段落内容
    assert any("a" * 500 in c for c in chunks)


def test_chunker_handles_oversized_single_paragraph():
    # 超过 hard_cap 的单段：按句子继续切
    big = "段落开头。" + "x" * 3000 + "。段落结尾。"
    chunks = chunk_text(big, target_chars=500, hard_cap=1000)
    assert all(len(c) <= 1100 for c in chunks)  # 大致符合 cap
    assert len(chunks) > 1


# ---------------- chunk_index 持久化 ----------------


def test_index_and_search_single_file(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    f = tmp_path / "long.md"
    f.write_text(
        "# 第一段\npython is great for data science.\n\n"
        "# 第二段\nrust is also good for systems.\n\n"
        "# 第三段\njavascript is everywhere on the web.\n"
    )
    n = index_path_chunks(engine, conv_id="c", path=f)
    assert n is not None and n >= 1
    hits = search_chunks(engine, conv_id="c", query="python")
    assert len(hits) >= 1
    assert hits[0].file_path == str(f)
    assert "python" in hits[0].chunk_text.lower()


def test_index_chunks_incremental_skip(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    f = tmp_path / "a.md"
    f.write_text("hello world")
    assert index_path_chunks(engine, conv_id="c", path=f) is not None
    # 再次索引未变化的文件 → None（跳过）
    assert index_path_chunks(engine, conv_id="c", path=f) is None


def test_chunk_per_conv_isolation(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    f = tmp_path / "shared.md"
    f.write_text("topic apple")
    index_path_chunks(engine, conv_id="conv_a", path=f)
    # 同样文件，conv_b 单独索引才能查到
    hits_b = search_chunks(engine, conv_id="conv_b", query="apple")
    assert hits_b == []
    index_path_chunks(engine, conv_id="conv_b", path=f)
    hits_b = search_chunks(engine, conv_id="conv_b", query="apple")
    assert len(hits_b) == 1


def test_index_directory_chunks_returns_stats(tmp_path):
    # 把 db 和数据目录分开，避免 db.sqlite 被 rglob 当成数据文件
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.md").write_text("第一份文档说苹果")
    (data / "b.md").write_text("第二份文档讲香蕉")
    stats = index_directory_chunks(engine, conv_id="c", root=data)
    assert stats["files"] == 2
    assert stats["chunks"] >= 2
    assert stats["skipped"] == 0
    stats2 = index_directory_chunks(engine, conv_id="c", root=data)
    assert stats2["files"] == 0
    assert stats2["skipped"] == 2


def test_chunk_stats(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    data = tmp_path / "data"
    data.mkdir()
    (data / "a.md").write_text("alpha")
    (data / "b.md").write_text("beta")
    index_directory_chunks(engine, conv_id="c", root=data)
    st = chunk_stats(engine, conv_id="c")
    assert st["files"] == 2
    assert st["chunks"] >= 2


# ---------------- SearchChunkTool ----------------


@pytest.fixture
def tool_ctx(tmp_path):
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    ctx = ToolContext(
        conv_id="c", agent_id="main", workspace=ws,
        memory_store=None,
        security=SecurityGate(workspace=ws),
        event_sink=QueueEventSink(),
        user_settings=None,
    )
    return ctx, engine


async def test_tool_returns_chunk_with_snippet(tool_ctx):
    ctx, engine = tool_ctx
    f = ctx.workspace.output_dir / "doc.md"
    f.write_text("第一段。\n\n这段提到了 pandas 的使用。\n\n第三段。")
    tool = SearchChunkTool(engine=engine)
    r = await tool.execute(
        SearchChunkTool.args_model(
            query="pandas", reindex_root=str(ctx.workspace.output_dir),
        ),
        ctx,
    )
    assert r.error is None
    assert "pandas" in r.content.lower()
    assert "段 " in r.content   # 段号信息
    # 命中后应该有 mv-file-list 卡片
    assert r.cards and r.cards[0].type == "mv-file-list"


async def test_tool_no_hits(tool_ctx):
    ctx, engine = tool_ctx
    tool = SearchChunkTool(engine=engine)
    r = await tool.execute(
        SearchChunkTool.args_model(query="impossiblestring_zzz_xxx"), ctx,
    )
    assert r.error is None
    assert "未找到" in r.content
