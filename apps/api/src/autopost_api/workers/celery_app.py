from __future__ import annotations

from celery import Celery

from autopost_api.config import settings

broker = settings.redis_url or "redis://localhost:6379/0"

celery_app = Celery("autopost", broker=broker, backend=broker)
celery_app.conf.update(
    timezone=settings.timezone,
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "dispatch-due-publish-jobs": {
            "task": "autopost_api.workers.tasks_publish.dispatch_due_jobs",
            "schedule": float(settings.beat_poll_seconds),
        },
    },
    imports=(
        "autopost_api.workers.tasks_generate",
        "autopost_api.workers.tasks_publish",
    ),
)
