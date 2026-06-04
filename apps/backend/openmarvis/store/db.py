from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlmodel import SQLModel
from sqlmodel import create_engine as _create_engine

from . import models as _models  # noqa: F401  ← 触发表注册


def create_engine(db_path: Path):
    Path(db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    return _create_engine(
        f"sqlite:///{Path(db_path).expanduser()}",
        connect_args={"check_same_thread": False},
    )


# SQLite 增量迁移：SQLModel.metadata.create_all 只会新建缺失的表，
# 不会为已存在的表加新列。每次为已有表增字段时，往此列表追加 (table, column, ddl)。
_ADDITIVE_COLUMNS: list[tuple[str, str, str]] = [
    ("memoryentry", "kind", "TEXT NOT NULL DEFAULT 'tool_result'"),
]


def _ensure_additive_columns(engine) -> None:
    with engine.connect() as conn:
        for table, col, ddl in _ADDITIVE_COLUMNS:
            cols = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            if not cols:
                continue  # 表还不存在；create_all 会带新字段建出来
            if any(row[1] == col for row in cols):
                continue  # 列已在
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
        conn.commit()


def init_db(engine) -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_additive_columns(engine)
    # FTS5 文件索引（独立于 SQLModel，因为 FTS 虚拟表 SQLModel 不支持）
    from .file_index import init_file_index
    init_file_index(engine)
