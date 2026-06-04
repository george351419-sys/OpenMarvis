from __future__ import annotations

import asyncio
import json
import os
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


def _resolve_llm_api_key(provider_model: str) -> str | None:
    """根据 provider_model 前缀选择对应 env 中的 key。

    走 openai/ 兼容端点（如混元）时优先 HUNYUAN_API_KEY，避免和真正的
    OPENAI_API_KEY 冲突。其它前缀（deepseek/、claude/）返回 None，让 litellm
    自己读 DEEPSEEK_API_KEY / ANTHROPIC_API_KEY。
    """
    if provider_model.startswith("openai/"):
        return os.getenv("HUNYUAN_API_KEY") or os.getenv("OPENAI_API_KEY")
    return None


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
                        api_key=_resolve_llm_api_key(settings.llm.provider_model),
                        max_tokens=settings.llm.max_tokens,
                        temperature=settings.llm.temperature,
                        vision_model=settings.llm.vision_model,
                        api_base=settings.llm.api_base)

    ask_registry = get_ask_registry(req.conv_id)
    agent = build_main_agent(
        conv_id=req.conv_id, llm=llm, engine=engine,
        brave_key=None,
        workspace=workspace, memory_store=memory, security=security,
        event_sink=sink, user_settings=settings, ask_registry=ask_registry,
        browser_pool=state.browser_pool,
        scheduler_manager=state.scheduler_manager,
        skill_registry=state.skill_registry,
    )

    async def run_agent():
        try:
            result = await agent.run(user_message=user_text, memory_ids=[])
            with Session(engine) as s:
                s.add(Message(conv_id=req.conv_id, role="assistant",
                               content=result.final_content,
                               created_at=int(time.time())))
                s.commit()
            # 产物校验
            from ..protocol.product_validator import validate_products
            from ..store.audit import writes_for_conv
            written = {w.path for w in writes_for_conv(engine, req.conv_id)}
            for issue in validate_products(result.final_content, written_paths=written):
                await sink.emit("warning", {"message": f"产物问题 [{issue.kind}]: {issue.detail}"})
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


async def _execute_scheduled_chat(virtual_conv_id: str, instruction: str,
                                    state) -> str:
    """供 ScheduleManager 触发使用：起一个独立 conversation 跑指令，返回最终回复。"""
    from sqlmodel import Session

    from ..agents.main_agent import build_main_agent
    from ..llm.client import LiteLLMClient
    from ..llm.event_sink import QueueEventSink
    from ..scheduler.trigger_filter import filter_registry_for_scheduled_run
    from ..security.policy import SecurityGate
    from ..store.models import Message

    engine = state.engine
    workspace = state.workspaces.get_or_create(virtual_conv_id)
    memory = state.memory
    settings = state.settings
    sink = QueueEventSink()
    security = SecurityGate(workspace=workspace,
                             extra_blocklist=settings.security.extra_path_blocklist)
    llm = LiteLLMClient(model=settings.llm.provider_model,
                         api_key=_resolve_llm_api_key(settings.llm.provider_model),
                         max_tokens=settings.llm.max_tokens,
                         temperature=settings.llm.temperature,
                         vision_model=settings.llm.vision_model,
                         api_base=settings.llm.api_base)

    agent = build_main_agent(
        conv_id=virtual_conv_id, llm=llm, engine=engine,
        brave_key=None,
        workspace=workspace, memory_store=memory, security=security,
        event_sink=sink, user_settings=settings, ask_registry=None,
        browser_pool=state.browser_pool,
        scheduler_manager=state.scheduler_manager,
        skill_registry=state.skill_registry,
    )
    # 替换 registry 为过滤后的版本（去掉 scheduler.* + ask_user）
    agent.tools = filter_registry_for_scheduled_run(agent.tools)
    user_text = f"[Scheduled Trigger]\n{instruction}"
    with Session(engine) as s:
        s.add(Message(conv_id=virtual_conv_id, role="user",
                       content=user_text, created_at=int(time.time())))
        s.commit()
    result = await agent.run(user_message=user_text, memory_ids=[])
    with Session(engine) as s:
        s.add(Message(conv_id=virtual_conv_id, role="assistant",
                       content=result.final_content,
                       created_at=int(time.time())))
        s.commit()
    return result.final_content
