from openmarvis.agents.main_agent import build_main_agent
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
