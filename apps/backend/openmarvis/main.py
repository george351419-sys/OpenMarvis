from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat_router, conversations_router, echo_router, files_router, settings_router
from .config import get_settings
from .deps import build_app_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.om = build_app_state()
    yield


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

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": "0.0.1"}

    return app


app = create_app()
