# LumenPost — Local run / 로컬 실행

> Canonical copy also lives in the Project Context store. This file ships with the repo for `git clone` users.

Phase 1 (own-site only). No Naver automation.

## Quick start

```bash
git clone <YOUR_REPO_URL>
cd <repo>
git checkout cursor/phase1-own-site-autopost-5e95   # or main after merge

cp .env.example .env
# Optional live Claude:
# ANTHROPIC_API_KEY=sk-ant-...

docker compose up --build
```

| Surface | URL |
|---------|-----|
| Blog + Admin | http://127.0.0.1:3847 |
| Admin | http://127.0.0.1:3847/admin |
| API health | http://127.0.0.1:8471/health |

Browser uses **same-origin** Next rewrites (`/api/*`, `/health` → FastAPI).

```bash
docker compose down          # stop
docker compose down -v       # stop + wipe Postgres volume
```

## Claude key

| `ANTHROPIC_API_KEY` | Behavior |
|---------------------|----------|
| empty | Mock Haiku + mock Sonnet review |
| set | Live Anthropic API |

## Without Docker

```bash
cp .env.example .env
cd apps/api && uv sync
uv run uvicorn autopost_api.main:app --host 0.0.0.0 --port 8471

# other terminal
cd apps/web && npm install && npm run dev
```

## Troubleshooting

**Port busy (3847 / 8471 / 5432 / 6379)** — `lsof -i :3847` and stop the other process, or change host ports in `docker-compose.yml`.

**Docker bridge broken (some Linux VMs)** —

```bash
docker compose -f docker-compose.host.yml up --build
```

(Not for Docker Desktop on Mac/Windows.)

**Admin blank / API errors** —

```bash
curl http://127.0.0.1:8471/health
curl http://127.0.0.1:3847/health    # via Next proxy
docker compose logs web api --tail 100
```

**Still mock with key set** — ensure repo-root `.env`, uncommented key, then `docker compose up -d --force-recreate api worker`.
