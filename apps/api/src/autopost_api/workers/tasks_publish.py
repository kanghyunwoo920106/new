from __future__ import annotations

import logging
import socket
from datetime import datetime, timezone

from sqlalchemy import select

from autopost_api.db.models import PublishJob
from autopost_api.db.session import SessionLocal
from autopost_api.services.publish_orchestrator import PublishOrchestrator
from autopost_api.workers.celery_app import celery_app

logger = logging.getLogger("autopost.publish")
WORKER_ID = socket.gethostname()


def claim_due_job_ids(limit: int = 50) -> list[str]:
    """Lock due publish_jobs (SKIP LOCKED on Postgres) and return ids."""
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
        rows = db.execute(q).scalars().all()
        ids: list[str] = []
        for job in rows:
            job.status = "locked"
            job.locked_by = WORKER_ID
            job.locked_at = now
            ids.append(str(job.id))
        db.commit()
        return ids
    finally:
        db.close()


@celery_app.task(name="autopost_api.workers.tasks_publish.dispatch_due_jobs")
def dispatch_due_jobs(limit: int = 50) -> int:
    ids = claim_due_job_ids(limit=limit)
    for jid in ids:
        publish_job_task.delay(jid)
    return len(ids)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60, name="autopost_api.workers.tasks_publish.publish_job_task")
def publish_job_task(self, job_id: str) -> dict:
    db = SessionLocal()
    try:
        job = db.get(PublishJob, job_id)
        if job is None or job.status not in {"locked", "queued"}:
            return {"skipped": True}
        job.status = "running"
        job.attempt += 1
        db.commit()
        db.refresh(job)
        _ = job.post
        result = PublishOrchestrator(db).publish(job)
        job.status = "succeeded"
        job.result_payload = result
        job.last_error = None
        db.commit()
        logger.info("published job=%s post=%s", job.id, job.post_id)
        return result
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.get(PublishJob, job_id)
        if job:
            job.last_error = str(exc)
            job.status = "queued" if job.attempt < job.max_attempts else "failed"
            db.commit()
        logger.exception("publish failed job=%s", job_id)
        raise self.retry(exc=exc)
    finally:
        db.close()
