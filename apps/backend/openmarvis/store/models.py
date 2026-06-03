from __future__ import annotations

from sqlmodel import Field, SQLModel


class Conversation(SQLModel, table=True):
    id: str = Field(primary_key=True)
    title: str = ""
    created_at: int = 0
    updated_at: int = 0
    archived: bool = False


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    conv_id: str = Field(index=True)
    role: str                          # user / assistant / tool
    content: str = ""
    thinking: str = ""
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_args_json: str | None = None
    tool_result_json: str | None = None
    memory_id: str | None = None
    created_at: int = 0


class MemoryEntry(SQLModel, table=True):
    id: str = Field(primary_key=True)   # memory_<ulid>
    conv_id: str = Field(index=True)
    content: str = ""
    created_at: int = 0


class SubAgentRecord(SQLModel, table=True):
    agent_id: str = Field(primary_key=True)
    conv_id: str = Field(index=True)
    agent_name: str
    status: str                          # running / completed / failed
    created_at: int = 0
    completed_at: int | None = None
    input_task: str = ""
    summary: str = ""
    full_content: str = ""
    messages_json: str = "[]"
    cards_json: str = "[]"


class WriteAudit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    conv_id: str = Field(index=True)
    path: str
    ts: int


class AuditLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ts: int
    conv_id: str
    agent_id: str
    tool: str
    args_hash: str = ""
    decision: str = ""
    duration_ms: int = 0
    exit_code: int | None = None
    error: str | None = None


class Schedule(SQLModel, table=True):
    id: str = Field(primary_key=True)
    origin_conv_id: str = Field(index=True)
    trigger_type: str                        # "once" / "interval" / "cron"
    trigger_spec: str
    instruction: str                          # 已脱敏的指令文本
    description: str = ""
    created_at: int = 0
    next_run_at: int | None = None
    last_run_at: int | None = None
    last_status: str | None = None            # "pending" / "success" / "failed"


class ScheduleNotification(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    origin_conv_id: str = Field(index=True)
    schedule_id: str = Field(index=True)
    virtual_conv_id: str
    summary: str = ""
    status: str = "success"                   # "success" / "failed"
    read: bool = False
    created_at: int = 0
