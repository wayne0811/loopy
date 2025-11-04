"""SQLModel models for Loopy."""

from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional
from datetime import datetime
from enum import Enum
import os
from pathlib import Path


class ItemStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class LoopItem(SQLModel, table=True):
    __tablename__ = "loop_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    loop_id: str = Field(foreign_key="loops.id")
    item: str
    status: ItemStatus = Field(default=ItemStatus.PENDING)
    attempts: int = Field(default=0)
    last_error: Optional[str] = Field(default=None)


class LoopModel(SQLModel, table=True):
    __tablename__ = "loops"

    id: str = Field(primary_key=True)
    command: str
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = Field(default="active")


def get_engine(db_path=None):
    if db_path is None:
        config_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        db_path = os.path.join(config_dir, "loopy", "db.sqlite")

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    return engine


def get_session(db_path=None):
    return Session(get_engine(db_path))
