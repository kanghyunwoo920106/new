# AutoPost API

FastAPI backend for LumenPost Phase 1.

## Modes

| Mode | When | DB | Scheduler |
|------|------|----|-----------|
| Docker Compose | `REDIS_URL` + Postgres set | PostgreSQL | Celery worker + Beat |
| Simple local | no Redis | SQLite | APScheduler in-process |

## Claude

Set `ANTHROPIC_API_KEY` in repo-root `.env` for live Haiku generate + Sonnet sample review.  
Empty key → mock (see root README).

## Commands

```bash
uv sync
uv run uvicorn autopost_api.main:app --host 0.0.0.0 --port 8471

# Celery (requires Redis + DATABASE_URL)
uv run celery -A autopost_api.workers.celery_app.celery_app worker --loglevel=INFO
uv run celery -A autopost_api.workers.celery_app.celery_app beat --loglevel=INFO
```
