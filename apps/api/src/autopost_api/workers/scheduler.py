from __future__ import annotations

import logging
import socket
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from autopost_api.config import settings
from autopost_api.db.models import PublishJob
from autopost_api.db.session import SessionLocal
from autopost_api.services.publish_orchestrator import PublishOrchestrator

logger = logging.getLogger("autopost.scheduler")
_scheduler: BackgroundScheduler | None = None
WORKER_ID = socket.gethostname()


def dispatch_due_jobs(limit: int = 50) -> int:
    """Local APScheduler path: claim due jobs and publish inline."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        q = (
            select(PublishJob)
            .where(PublishJob.status == "queued", PublishJob.run_at <= now)
            .order_by(PublishJob.run_at)
            .limit(limit)
        )
        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            q = q.with_for_update(skip_locked=True)
        jobs = db.execute(q).scalars().all()
        count = 0
        for job in jobs:
            job.status = "running"
            job.attempt += 1
            job.locked_by = WORKER_ID
            job.locked_at = now
            db.commit()
            try:
                db.refresh(job)
                _ = job.post
                result = PublishOrchestrator(db).publish(job)
                job.status = "succeeded"
                job.result_payload = result
                job.last_error = None
                db.commit()
                count += 1
                logger.info("published job=%s post=%s", job.id, job.post_id)
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                job = db.get(PublishJob, job.id)
                if job is None:
                    continue
                job.last_error = str(exc)
                job.status = "queued" if job.attempt < job.max_attempts else "failed"
                db.commit()
                logger.exception("publish failed job=%s", job.id)
        return count
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        dispatch_due_jobs,
        "interval",
        seconds=settings.beat_poll_seconds,
        id="dispatch-due-publish-jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if settings.autopilot_enabled:
        from autopost_api.services.autopilot import run_autopilot

        for hour, minute in settings.autopilot_clock_times():
            scheduler.add_job(
                run_autopilot,
                "cron",
                hour=hour,
                minute=minute,
                timezone=settings.timezone,
                id=f"autopilot-{hour:02d}{minute:02d}",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=3600,
            )
        logger.info(
            "autopilot at %s channels=%s",
            settings.autopilot_time_label(),
            settings.autopilot_channels,
        )
    scheduler.start()
    _scheduler = scheduler
    logger.info("APScheduler started (poll=%ss)", settings.beat_poll_seconds)
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
