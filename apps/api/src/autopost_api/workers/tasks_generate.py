from __future__ import annotations

import logging

from autopost_api.db.models import Batch
from autopost_api.db.session import SessionLocal
from autopost_api.services.batch_pipeline import process_batch
from autopost_api.workers.celery_app import celery_app

logger = logging.getLogger("autopost.generate")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=15, name="autopost_api.workers.tasks_generate.process_batch_task")
def process_batch_task(self, batch_id: str) -> str:
    db = SessionLocal()
    try:
        process_batch(db, batch_id)
        return batch_id
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        batch = db.get(Batch, batch_id)
        if batch and self.request.retries >= self.max_retries:
            batch.status = "failed"
            db.commit()
        logger.exception("batch generate failed id=%s", batch_id)
        raise self.retry(exc=exc)
    finally:
        db.close()
