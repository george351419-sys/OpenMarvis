import pytest

from openmarvis.memory.store import USER_PREF_CONV_ID, MemoryStore
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


async def test_user_pref_round_trip(engine):
    store = MemoryStore(engine)
    a = await store.put(conv_id=USER_PREF_CONV_ID, content="不用 emoji",
                          kind="user_pref")
    b = await store.put(conv_id=USER_PREF_CONV_ID, content="文件默认 ~/Desktop",
                          kind="user_pref")
    # 与 tool_result memory 混存，互不污染
    await store.put(conv_id="conv_x", content="some big tool result")
    prefs = await store.fetch_user_prefs()
    ids = {p.id for p in prefs}
    assert {a, b} <= ids
    assert all(p.kind == "user_pref" for p in prefs)
    assert all(p.conv_id == USER_PREF_CONV_ID for p in prefs)
    contents = [p.content for p in prefs]
    # 旧的在前
    assert contents.index("不用 emoji") < contents.index("文件默认 ~/Desktop")


async def test_delete_user_pref_only_removes_prefs(engine):
    store = MemoryStore(engine)
    pref = await store.put(conv_id=USER_PREF_CONV_ID, content="X",
                            kind="user_pref")
    tool = await store.put(conv_id="conv_a", content="Y")  # tool_result
    # 删 user_pref OK
    assert await store.delete_user_pref(pref_id=pref) is True
    # 试图通过 delete_user_pref 删 tool_result 应被拒（不是 user_pref）
    assert await store.delete_user_pref(pref_id=tool) is False
    # 不存在
    assert await store.delete_user_pref(pref_id="memory_missing") is False


async def test_summarize_preview_truncates(engine):
    store = MemoryStore(engine)
    long_text = "abc" * 500
    summary = store.summarize_preview(long_text, max_chars=80)
    assert len(summary) <= 80 + len("...")
    assert summary.startswith("abc")
