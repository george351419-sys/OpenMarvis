"""Regression: 旧 DB 不带 memoryentry.kind 字段时，init_db 应自动补列。"""
from __future__ import annotations

from sqlalchemy import text

from openmarvis.store.db import create_engine, init_db


def test_init_db_adds_kind_to_legacy_memoryentry(tmp_path):
    db_path = tmp_path / "legacy.sqlite"
    engine = create_engine(db_path)
    # 模拟旧 schema：手动建一个不带 kind 列的 memoryentry
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE TABLE memoryentry ("
            "id TEXT PRIMARY KEY, conv_id TEXT, content TEXT, created_at INTEGER)"
        ))
        conn.execute(text(
            "INSERT INTO memoryentry (id, conv_id, content, created_at) "
            "VALUES ('memory_old', 'conv_a', 'legacy', 0)"
        ))
        conn.commit()

    init_db(engine)  # 应该补 kind 列、不报错

    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text(
            "PRAGMA table_info(memoryentry)"
        )).fetchall()}
        assert "kind" in cols
        # 旧记录的 kind 默认为 'tool_result'
        row = conn.execute(text(
            "SELECT kind FROM memoryentry WHERE id='memory_old'"
        )).fetchone()
        assert row is not None and row[0] == "tool_result"


def test_init_db_is_idempotent(tmp_path):
    # 跑两次不应出错
    engine = create_engine(tmp_path / "x.sqlite")
    init_db(engine)
    init_db(engine)
