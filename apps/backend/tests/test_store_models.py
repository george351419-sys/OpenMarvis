from sqlmodel import Session, select

from openmarvis.store.db import create_engine, init_db
from openmarvis.store.models import Conversation, MemoryEntry, Message, SubAgentRecord, WriteAudit


def test_models_round_trip(tmp_path):
    engine = create_engine(tmp_path / "db.sqlite")
    init_db(engine)
    with Session(engine) as s:
        conv = Conversation(id="conv_a", title="hello")
        s.add(conv)
        s.add(Message(conv_id="conv_a", role="user", content="hi"))
        s.add(MemoryEntry(id="memory_1", conv_id="conv_a", content="X" * 100))
        s.add(SubAgentRecord(agent_id="sa_1", conv_id="conv_a", agent_name="file-agent",
                             status="completed", input_task="t", summary="s", full_content="f",
                             messages_json="[]", cards_json="[]"))
        s.add(WriteAudit(conv_id="conv_a", path="/tmp/x", ts=1))
        s.commit()
    with Session(engine) as s:
        assert s.exec(select(Conversation)).first().title == "hello"
        assert s.exec(select(Message)).first().content == "hi"
        assert s.exec(select(MemoryEntry)).first().id == "memory_1"
        assert s.exec(select(SubAgentRecord)).first().agent_name == "file-agent"
        assert s.exec(select(WriteAudit)).first().path == "/tmp/x"
