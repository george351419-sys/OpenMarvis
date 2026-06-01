import pytest

from openmarvis.memory.store import MemoryStore
from openmarvis.store.db import create_engine, init_db


@pytest.fixture
def engine(tmp_path):
    e = create_engine(tmp_path / "db.sqlite")
    init_db(e)
    return e


async def test_put_returns_prefixed_id(engine):
    store = MemoryStore(engine)
    mid = await store.put(conv_id="conv_a", content="X" * 100)
    assert mid.startswith("memory_")


async def test_fetch_returns_content(engine):
    store = MemoryStore(engine)
    mid = await store.put(conv_id="conv_a", content="hello world")
    fetched = await store.fetch(["memory_missing", mid], conv_id="conv_a")
    assert len(fetched) == 1
    assert fetched[0].content == "hello world"


async def test_fetch_filters_by_conv_id(engine):
    store = MemoryStore(engine)
    mid = await store.put(conv_id="conv_a", content="x")
    other = await store.fetch([mid], conv_id="conv_b")
    assert other == []


async def test_summarize_preview_truncates(engine):
    store = MemoryStore(engine)
    long_text = "abc" * 500
    summary = store.summarize_preview(long_text, max_chars=80)
    assert len(summary) <= 80 + len("...")
    assert summary.startswith("abc")
