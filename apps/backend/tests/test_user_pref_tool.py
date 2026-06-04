import pytest

from openmarvis.llm.event_sink import QueueEventSink
from openmarvis.memory.store import USER_PREF_CONV_ID, MemoryStore
from openmarvis.security.policy import SecurityGate
from openmarvis.store.db import create_engine, init_db
from openmarvis.tools.base import ToolContext
from openmarvis.tools.user_pref import (
    ForgetUserPreferenceTool,
    SaveUserPreferenceTool,
)
from openmarvis.workspace.manager import Workspace


@pytest.fixture
def ctx(tmp_path):
    ws = Workspace(conv_id="conv_a", root_base=tmp_path)
    ws.ensure()
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    return ToolContext(
        conv_id="conv_a", agent_id="main", workspace=ws,
        memory_store=MemoryStore(engine),
        security=SecurityGate(workspace=ws),
        event_sink=QueueEventSink(),
        user_settings=None,
    )


async def test_save_and_forget_round_trip(ctx):
    save = SaveUserPreferenceTool()
    r = await save.execute(SaveUserPreferenceTool.args_model(rule="不要用 emoji"), ctx)
    assert r.error is None
    # 内容写到了 USER_PREF_CONV_ID 下、kind='user_pref'
    prefs = await ctx.memory_store.fetch_user_prefs()
    assert len(prefs) == 1
    pref_id = prefs[0].id
    assert prefs[0].content == "不要用 emoji"

    forget = ForgetUserPreferenceTool()
    r2 = await forget.execute(
        ForgetUserPreferenceTool.args_model(pref_id=pref_id), ctx,
    )
    assert r2.error is None
    assert await ctx.memory_store.fetch_user_prefs() == []


async def test_save_rejects_empty_and_too_long(ctx):
    save = SaveUserPreferenceTool()
    r = await save.execute(SaveUserPreferenceTool.args_model(rule="   "), ctx)
    assert r.error == "rule_empty"
    r2 = await save.execute(
        SaveUserPreferenceTool.args_model(rule="x" * 501), ctx,
    )
    assert r2.error is not None and "rule_too_long" in r2.error


async def test_forget_rejects_non_pref_memory(ctx):
    # tool_result 类的 memory 不能用 forget_user_preference 删
    mid = await ctx.memory_store.put(conv_id="conv_a", content="tool result")
    forget = ForgetUserPreferenceTool()
    r = await forget.execute(
        ForgetUserPreferenceTool.args_model(pref_id=mid), ctx,
    )
    assert r.error is not None and "pref_not_found" in r.error


async def test_user_pref_conv_id_is_global(ctx):
    # 不论在哪个 conv 调，写到的都是 _global
    save = SaveUserPreferenceTool()
    await save.execute(SaveUserPreferenceTool.args_model(rule="rule X"), ctx)
    prefs = await ctx.memory_store.fetch_user_prefs()
    assert prefs[0].conv_id == USER_PREF_CONV_ID
