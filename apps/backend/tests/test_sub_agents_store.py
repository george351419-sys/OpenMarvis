import pytest

from openmarvis.store.db import create_engine, init_db
from openmarvis.store.sub_agents import SubAgentStore


@pytest.fixture
def store(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    return SubAgentStore(engine)


async def test_save_and_load_full(store):
    await store.save(agent_id="sa-1", conv_id="c", agent_name="file-agent",
                     status="completed", input_task="t", summary="s",
                     full_content="hello full", messages_json="[]", cards_json="[]")
    full = await store.get_full(agent_id="sa-1", conv_id="c")
    assert full is not None
    assert full["full_content"] == "hello full"


async def test_get_full_filters_by_conv(store):
    await store.save(agent_id="sa-2", conv_id="c", agent_name="file-agent",
                     status="completed", input_task="t", summary="s",
                     full_content="x", messages_json="[]", cards_json="[]")
    assert await store.get_full(agent_id="sa-2", conv_id="other") is None


async def test_try_inherit_returns_messages(store):
    await store.save(agent_id="sa-3", conv_id="c", agent_name="file-agent",
                     status="completed", input_task="t", summary="s",
                     full_content="x", messages_json='[{"role":"user","content":"hi"}]',
                     cards_json="[]")
    msgs = await store.try_inherit(target_agent_name="file-agent",
                                   source_id="sa-3", conv_id="c")
    assert msgs and msgs[0]["content"] == "hi"


async def test_try_inherit_rejects_mismatched_name(store):
    await store.save(agent_id="sa-4", conv_id="c", agent_name="search-agent",
                     status="completed", input_task="t", summary="s",
                     full_content="x", messages_json="[]", cards_json="[]")
    msgs = await store.try_inherit(target_agent_name="file-agent",
                                   source_id="sa-4", conv_id="c")
    assert msgs is None
