from __future__ import annotations

from dataclasses import dataclass

from .browser.pool import BrowserPool
from .config import Settings, get_settings
from .memory.store import MemoryStore
from .store.db import create_engine, init_db
from .workspace.manager import WorkspaceManager


@dataclass
class AppState:
    settings: Settings
    engine: object
    workspaces: WorkspaceManager
    memory: MemoryStore
    browser_pool: BrowserPool
    scheduler_manager: object | None = None
    skill_registry: object | None = None


def build_app_state() -> AppState:
    settings = get_settings(refresh=True)
    settings.workspace.root.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.workspace.root / "data.db")
    init_db(engine)
    workspaces = WorkspaceManager(root_base=settings.workspace.root)
    memory = MemoryStore(engine)
    browser_pool = BrowserPool(settings=settings.browser,
                                profile_dir_base=settings.workspace.root / "browser-profile")
    try:
        from .computer.permission_probe import probe_permissions
        probe_permissions()
    except Exception:
        pass
    try:
        from .app_automation.permission_probe import probe_app_automation_permissions
        probe_app_automation_permissions()
    except Exception:
        pass

    from .scheduler.manager import ScheduleManager
    from .scheduler.trigger_runner import run_scheduled_trigger
    from .store.notifications import persist_notification

    def _load_schedule(engine_, sid: str):
        from sqlmodel import Session, select

        from .store.models import Schedule
        with Session(engine_) as ses:
            return ses.exec(select(Schedule).where(Schedule.id == sid)).first()

    # Use a holder so the closure captures the eventually-bound app_state.
    _holder: dict = {"state": None}

    async def _run_chat_for_schedule(virtual_conv_id, instruction, state):
        from .api.chat import _execute_scheduled_chat
        return await _execute_scheduled_chat(virtual_conv_id, instruction, state)

    async def _on_fire(sid: str):
        state_ref = _holder["state"]
        if state_ref is None:
            return
        await run_scheduled_trigger(
            schedule_id=sid,
            state=state_ref,
            load_schedule=_load_schedule,
            run_chat=_run_chat_for_schedule,
            persist_notification=persist_notification,
        )

    scheduler_manager = ScheduleManager(
        db_dir=settings.workspace.root,
        engine=engine,
        on_fire=_on_fire,
    )

    from pathlib import Path

    from .skill.registry import SkillRegistry
    skill_registry = SkillRegistry()
    builtins_root = Path(__file__).parent / "skill" / "builtins"
    user_skills = settings.workspace.root / "skills"
    skill_registry.scan(builtins_root, user_skills)

    state = AppState(settings=settings, engine=engine, workspaces=workspaces,
                    memory=memory, browser_pool=browser_pool,
                    scheduler_manager=scheduler_manager,
                    skill_registry=skill_registry)
    _holder["state"] = state
    return state
