from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlmodel import Session
from sse_starlette.sse import EventSourceResponse

from ..agents.main_agent import build_main_agent
from ..llm.client import LiteLLMClient
from ..llm.event_sink import QueueEventSink
from ..security.policy import SecurityGate
from ..store.models import Message
from ..tools.ask import PendingAskRegistry

router = APIRouter(tags=["chat"])

_ASK_REGISTRIES: dict[str, PendingAskRegistry] = {}


def get_ask_registry(conv_id: str) -> PendingAskRegistry:
    return _ASK_REGISTRIES.setdefault(conv_id, PendingAskRegistry())


class ChatRequest(BaseModel):
    conv_id: str
    message: str
    attachments: list[str] = []


def _wrap_user_message(message: str, attachments: list[str]) -> str:
    if not attachments:
        return message
    block = "\n".join(attachments)
    return (f"<user_message>\n{message}\n</user_message>\n"
            f"<attachments>\n{block}\n</attachments>")


@router.post("/chat")
async def chat(req: ChatRequest, request: Request) -> EventSourceResponse:
    state = request.app.state.om
    engine = state.engine
    workspace = state.workspaces.get_or_create(req.conv_id)
    memory = state.memory
    settings = state.settings
    sink = QueueEventSink()
    security = SecurityGate(workspace=workspace,
                            extra_blocklist=settings.security.extra_path_blocklist)

    user_text = _wrap_user_message(req.message, req.attachments)
    with Session(engine) as s:
        s.add(Message(conv_id=req.conv_id, role="user",
                       content=user_text, created_at=int(time.time())))
        s.commit()

    llm = LiteLLMClient(model=settings.llm.provider_model,
                        max_tokens=settings.llm.max_tokens,
                        temperature=settings.llm.temperature)

    ask_registry = get_ask_registry(req.conv_id)
    agent = build_main_agent(
        conv_id=req.conv_id, llm=llm, engine=engine,
        brave_key=None,
        workspace=workspace, memory_store=memory, security=security,
        event_sink=sink, user_settings=settings, ask_registry=ask_registry,
    )

    async def run_agent():
        try:
            result = await agent.run(user_message=user_text, memory_ids=[])
            with Session(engine) as s:
                s.add(Message(conv_id=req.conv_id, role="assistant",
                               content=result.final_content,
                               created_at=int(time.time())))
                s.commit()
            await sink.emit("done", {"final_content": result.final_content})
        except Exception as e:  # noqa: BLE001
            await sink.emit("error", {"message": str(e), "recoverable": False})
        finally:
            await sink.close()

    asyncio.create_task(run_agent())

    async def event_stream() -> AsyncIterator[dict]:
        async for ev, data in sink.drain():
            yield {"event": ev, "data": json.dumps(data, ensure_ascii=False)}

    return EventSourceResponse(event_stream())


class AnswerAskRequest(BaseModel):
    conv_id: str
    ask_id: str
    choices: list[str]


@router.post("/asks/answer")
async def answer_ask(req: AnswerAskRequest) -> dict:
    reg = get_ask_registry(req.conv_id)
    await reg.resolve(req.ask_id, req.choices)
    return {"ok": True}
