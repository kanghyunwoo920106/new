from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from autopost_api.api.schemas import HealthOut
from autopost_api.api.v1.router import api_router
from autopost_api.config import settings
from autopost_api.db.models import Base
from autopost_api.db.seed import seed_if_empty
from autopost_api.db.session import SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autopost")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()

    if settings.use_celery:
        logger.info("Celery mode — Beat/worker own due-job polling (no in-process APScheduler)")
    else:
        from autopost_api.workers.scheduler import start_scheduler

        start_scheduler()

    logger.info(
        "API ready mock_claude=%s db=%s scheduler=%s",
        settings.use_mock_claude,
        settings.database_url.split("://")[0],
        settings.effective_scheduler,
    )
    yield
    if not settings.use_celery:
        from autopost_api.workers.scheduler import stop_scheduler

        stop_scheduler()


app = FastAPI(title="AutoPost API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(
        status="ok",
        mock_claude=settings.use_mock_claude,
        database=settings.database_url.split("://")[0],
        scheduler=settings.effective_scheduler,
        configured_channels=settings.configured_channels,
    )


def run() -> None:
    import uvicorn

    uvicorn.run(
        "autopost_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()
