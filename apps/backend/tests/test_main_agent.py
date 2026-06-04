from openmarvis.agents.main_agent import build_main_agent
from openmarvis.config import Settings
from openmarvis.llm.event_sink import QueueEventSink
from openmarvis.memory.store import MemoryStore
from openmarvis.security.policy import SecurityGate
from openmarvis.store.db import create_engine, init_db
from openmarvis.workspace.manager import Workspace


def test_main_prompt_contains_workspace_paths(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()

    class FakeLLM:
        pass

    agent = build_main_agent(
        conv_id="c", llm=FakeLLM(), engine=engine, brave_key=None,
        workspace=ws, memory_store=MemoryStore(engine),
        security=SecurityGate(workspace=ws), event_sink=QueueEventSink(),
        user_settings=None,
    )
    assert str(ws.output_dir) in agent.system_prompt
    tool_names = {t.name for t in agent.tools.all()}
    assert {"dispatch_task", "present_result", "ask_user",
            "read_text", "write_file", "web_search", "web_fetch"}.issubset(tool_names)


def test_build_main_agent_attaches_managers_to_real_settings(tmp_path):
    # Regression: chat path used to crash because build_main_agent set
    # user_settings.scheduler_manager on a real Settings() instance, which
    # pydantic rejected (no such field) → /chat returned 500 before SSE.
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    ws = Workspace(conv_id="c", root_base=tmp_path)
    ws.ensure()

    class FakeLLM:
        pass

    settings = Settings()
    fake_mgr = object()
    fake_skills = object()
    agent = build_main_agent(
        conv_id="c", llm=FakeLLM(), engine=engine, brave_key=None,
        workspace=ws, memory_store=MemoryStore(engine),
        security=SecurityGate(workspace=ws), event_sink=QueueEventSink(),
        user_settings=settings,
        scheduler_manager=fake_mgr, skill_registry=fake_skills,
    )
    assert settings.scheduler_manager is fake_mgr
    tool_names = {t.name for t in agent.tools.all()}
    assert "use_skill" in tool_names  # skill_registry path also exercised
