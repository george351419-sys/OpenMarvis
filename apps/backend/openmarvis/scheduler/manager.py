from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

log = logging.getLogger(__name__)


class ScheduleSpecError(ValueError):
    """trigger_spec 非法。"""


@dataclass
class ScheduleRow:
    id: str
    origin_conv_id: str
    trigger_type: str
    trigger_spec: str
    instruction: str
    description: str
    next_run_at: datetime | None


def _now_ts() -> int:
    return int(datetime.now(UTC).timestamp())


def _new_sid() -> str:
    return f"sch_{uuid.uuid4().hex[:12]}"


class ScheduleManager:
    """APScheduler 单例包装，提供 once/interval/cron 三种触发。"""

    def __init__(self, *, db_dir: Path, engine,
                 on_fire: Callable[[str], Awaitable[None] | None]):
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.engine = engine
        self._on_fire = on_fire
        # Use MemoryJobStore: APScheduler can't serialize closures to SQL.
        # Durable persistence is via the Schedule SQLModel table (_persist below);
        # lifespan rehydration of scheduled jobs is handled by the caller.
        self._sched = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()}, timezone="UTC")

    async def start(self) -> None:
        self._sched.start()

    async def shutdown(self) -> None:
        self._sched.shutdown(wait=False)

    def rehydrate(self) -> int:
        """重启后把 Schedule 表里的行重新挂回 APScheduler。

        - `once` 触发时间已过 → 跳过（不补跑）。
        - 已经在 scheduler 里的 sid → 跳过（idempotent）。
        返回成功加载的 job 数。
        """
        if self.engine is None:
            return 0
        from sqlmodel import Session, select

        from ..store.models import Schedule
        loaded = 0
        existing = {j.id for j in self._sched.get_jobs()}
        now = datetime.now(UTC)
        with Session(self.engine) as ses:
            rows = ses.exec(select(Schedule)).all()
        for r in rows:
            if r.id in existing:
                continue
            try:
                if r.trigger_type == "once":
                    run_at = datetime.fromisoformat(r.trigger_spec)
                    if run_at <= now:
                        log.info("skip past-due once schedule %s", r.id)
                        continue
                    trig = DateTrigger(run_date=run_at)
                elif r.trigger_type == "interval":
                    trig = IntervalTrigger(seconds=int(r.trigger_spec))
                elif r.trigger_type == "cron":
                    trig = CronTrigger.from_crontab(r.trigger_spec)
                else:
                    log.warning("unknown trigger_type %s on %s",
                                 r.trigger_type, r.id)
                    continue
                self._sched.add_job(self._wrap_callback(r.id), trigger=trig,
                                     id=r.id, name=r.description or r.trigger_type,
                                     replace_existing=False)
                loaded += 1
            except Exception:
                log.exception("rehydrate failed for %s", r.id)
        return loaded

    def _wrap_callback(self, sid: str):
        async def _fn():
            result = self._on_fire(sid)
            if hasattr(result, "__await__"):
                await result
        return _fn

    def add_once(self, run_at: datetime, *, instruction: str, description: str,
                  origin_conv_id: str) -> str:
        sid = _new_sid()
        trig = DateTrigger(run_date=run_at)
        self._sched.add_job(self._wrap_callback(sid), trigger=trig,
                             id=sid, name=description or "once",
                             replace_existing=True)
        self._persist(sid, "once", run_at.isoformat(),
                       instruction, description, origin_conv_id)
        return sid

    def add_interval(self, *, every_seconds: int, instruction: str,
                      description: str, origin_conv_id: str) -> str:
        if every_seconds < 60:
            raise ScheduleSpecError("interval 不得小于 60 秒")
        sid = _new_sid()
        trig = IntervalTrigger(seconds=every_seconds)
        self._sched.add_job(self._wrap_callback(sid), trigger=trig,
                             id=sid, name=description or "interval",
                             replace_existing=True)
        self._persist(sid, "interval", str(every_seconds),
                       instruction, description, origin_conv_id)
        return sid

    def add_cron(self, *, expr: str, instruction: str,
                  description: str, origin_conv_id: str) -> str:
        try:
            trig = CronTrigger.from_crontab(expr)
        except Exception as e:
            raise ScheduleSpecError(f"无效 cron 表达式: {e}") from e
        sid = _new_sid()
        self._sched.add_job(self._wrap_callback(sid), trigger=trig,
                             id=sid, name=description or "cron",
                             replace_existing=True)
        self._persist(sid, "cron", expr, instruction, description, origin_conv_id)
        return sid

    def list(self) -> list[ScheduleRow]:
        out: list[ScheduleRow] = []
        for job in self._sched.get_jobs():
            row = self._read_row(job.id)
            if row is None:
                continue
            row.next_run_at = job.next_run_time
            out.append(row)
        return out

    def cancel(self, sid: str) -> bool:
        try:
            self._sched.remove_job(sid)
        except Exception:
            return False
        self._delete_row(sid)
        return True

    def modify(self, sid: str, *,
               trigger_type: str | None = None,
               trigger_spec: str | None = None,
               instruction: str | None = None,
               description: str | None = None) -> bool:
        """Modify an existing schedule. Returns False if not found."""
        row = self._read_row(sid)
        if row is None:
            return False

        new_type = trigger_type or row.trigger_type
        new_spec = trigger_spec or row.trigger_spec
        new_instr = instruction if instruction is not None else row.instruction
        new_desc = description if description is not None else row.description

        try:
            if new_type == "once":
                run_at = datetime.fromisoformat(new_spec)
                trig = DateTrigger(run_date=run_at)
            elif new_type == "interval":
                secs = int(new_spec)
                if secs < 60:
                    raise ScheduleSpecError("interval 不得小于 60 秒")
                trig = IntervalTrigger(seconds=secs)
            elif new_type == "cron":
                trig = CronTrigger.from_crontab(new_spec)
            else:
                raise ScheduleSpecError(f"未知触发类型: {new_type}")
        except ScheduleSpecError:
            raise
        except Exception as e:
            raise ScheduleSpecError(f"trigger_spec 解析失败: {e}") from e

        try:
            self._sched.remove_job(sid)
        except Exception:
            pass
        self._sched.add_job(self._wrap_callback(sid), trigger=trig,
                             id=sid, name=new_desc or new_type,
                             replace_existing=True)
        self._update_row(sid, new_type, new_spec, new_instr, new_desc)
        return True

    # -- persistence ---------------------------------------------------------

    def _persist(self, sid: str, trigger_type: str, trigger_spec: str,
                  instruction: str, description: str, origin_conv_id: str) -> None:
        if self.engine is None:
            return
        from sqlmodel import Session

        from ..store.models import Schedule
        with Session(self.engine) as ses:
            ses.add(Schedule(
                id=sid, origin_conv_id=origin_conv_id,
                trigger_type=trigger_type, trigger_spec=trigger_spec,
                instruction=instruction, description=description,
                created_at=_now_ts(),
            ))
            ses.commit()

    def _read_row(self, sid: str) -> ScheduleRow | None:
        if self.engine is None:
            return ScheduleRow(id=sid, origin_conv_id="?", trigger_type="?",
                                trigger_spec="?", instruction="?",
                                description="?", next_run_at=None)
        from sqlmodel import Session, select

        from ..store.models import Schedule
        with Session(self.engine) as ses:
            r = ses.exec(select(Schedule).where(Schedule.id == sid)).first()
            if r is None:
                return None
            return ScheduleRow(id=r.id, origin_conv_id=r.origin_conv_id,
                                trigger_type=r.trigger_type,
                                trigger_spec=r.trigger_spec,
                                instruction=r.instruction,
                                description=r.description,
                                next_run_at=None)

    def _update_row(self, sid: str, trigger_type: str, trigger_spec: str,
                    instruction: str, description: str) -> None:
        if self.engine is None:
            return
        from sqlmodel import Session, select

        from ..store.models import Schedule
        with Session(self.engine) as ses:
            r = ses.exec(select(Schedule).where(Schedule.id == sid)).first()
            if r is not None:
                r.trigger_type = trigger_type
                r.trigger_spec = trigger_spec
                r.instruction = instruction
                r.description = description
                ses.commit()

    def _delete_row(self, sid: str) -> None:
        if self.engine is None:
            return
        from sqlmodel import Session, select

        from ..store.models import Schedule
        with Session(self.engine) as ses:
            r = ses.exec(select(Schedule).where(Schedule.id == sid)).first()
            if r is not None:
                ses.delete(r)
                ses.commit()
