from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from autopost_api.config import settings
from autopost_api.db.models import Batch
from autopost_api.db.session import SessionLocal
from autopost_api.services.batch_pipeline import process_batch

logger = logging.getLogger("autopost.enqueue")
_pool = ThreadPoolExecutor(max_workers=2)


def _run_batch_inline(batch_id: str) -> None:
    db = SessionLocal()
    try:
        process_batch(db, batch_id)
    except Exception:
        batch = db.get(Batch, batch_id)
        if batch:
            batch.status = "failed"
            db.commit()
        logger.exception("inline batch failed id=%s", batch_id)
    finally:
        db.close()


def enqueue_batch(batch_id: str) -> str:
    """Enqueue batch generation via Celery when available, else background thread."""
    if settings.use_celery:
        from autopost_api.workers.tasks_generate import process_batch_task

        process_batch_task.delay(batch_id)
        return "celery"
    _pool.submit(_run_batch_inline, batch_id)
    return "thread"
