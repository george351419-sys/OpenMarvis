from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel
from sqlmodel import create_engine as _create_engine

from . import models as _models  # noqa: F401  ← 触发表注册


def create_engine(db_path: Path):
    Path(db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    return _create_engine(
        f"sqlite:///{Path(db_path).expanduser()}",
        connect_args={"check_same_thread": False},
    )


def init_db(engine) -> None:
    SQLModel.metadata.create_all(engine)
