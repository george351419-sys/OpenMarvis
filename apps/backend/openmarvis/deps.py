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
    return AppState(settings=settings, engine=engine, workspaces=workspaces,
                    memory=memory, browser_pool=browser_pool)
