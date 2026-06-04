from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 在任何 config / litellm 读 env 之前加载 apps/backend/.env（若存在）。
# override=False：已有的 shell 环境变量优先，CI 不会被覆盖。
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

from .api import (
    chat_router,
    conversations_router,
    echo_router,
    files_router,
    notifications_router,
    schedules_router,
    settings_router,
    skills_router,
)
from .config import get_settings
from .deps import build_app_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.om = build_app_state()
    await app.state.om.scheduler_manager.start()
    app.state.om.scheduler_manager.rehydrate()
    try:
        yield
    finally:
        try:
            await app.state.om.scheduler_manager.shutdown()
        except Exception:
            pass
        try:
            await app.state.om.browser_pool.shutdown()
        except Exception:
            pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="OpenMarvis", version="0.0.1", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(echo_router)
    app.include_router(conversations_router)
    app.include_router(files_router)
    app.include_router(chat_router)
    app.include_router(settings_router)
    app.include_router(notifications_router)
    app.include_router(schedules_router)
    app.include_router(skills_router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": "0.0.1"}

    return app


app = create_app()
