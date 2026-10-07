# 루멘포스트 (LumenPost) — Phase 1

AI로 한국어 블로그 글을 생성·예약하고 **자체 사이트에만** 자동 발행합니다.  
네이버 자동화는 Phase 1 범위 밖입니다.

**로컬 실행 상세 / Local run details:** [docs/local-run.md](./docs/local-run.md)

## What works

1. 비민감 카테고리 allowlist → Claude(또는 mock) 주제 **10개** 추천  
2. 주제 선택 → **2,000자+** 본문 + SEO 태그 일괄 생성  
3. **즉시 발행** 또는 **`sequential_cycle`** 예약 (`4h` / `12h` / `24h` / `2d` / `1w`)  
4. Celery Beat (또는 APScheduler)가 `publish_jobs.run_at` due job을 발행  
5. 공개 블로그 + 운영 UI  
6. AdSense **placeholder** 슬롯  
7. 배치 첫 글 + 약 15% Sonnet 샘플 검수  

## Stack

| Layer | Docker Compose (recommended) | Simple local-dev |
|-------|------------------------------|------------------|
| API | FastAPI | FastAPI |
| Web | Next.js (same-origin `/api` rewrite → API) | Next.js |
| DB | **PostgreSQL 16** | SQLite |
| Queue / schedule | **Redis + Celery worker + Beat** | APScheduler in API |
| AI | Claude Haiku + Sonnet sample; mock if no key | same |

---

## Local run / 로컬 실행 (laptop)

### English

```bash
git clone <YOUR_REPO_URL> && cd <repo>
git checkout cursor/phase1-own-site-autopost-5e95   # or main after merge

cp .env.example .env
# optional live Claude:
# ANTHROPIC_API_KEY=sk-ant-...

docker compose up --build
```

- Blog + Admin: **http://127.0.0.1:3847**  
- Admin: **http://127.0.0.1:3847/admin**  
- API health: **http://127.0.0.1:8471/health** (also proxied at `/health` on the web origin)

### 한국어

```bash
git clone <저장소_URL> && cd <repo>
git checkout cursor/phase1-own-site-autopost-5e95

cp .env.example .env
# 선택: 실제 Claude 사용 시
# ANTHROPIC_API_KEY=sk-ant-...

docker compose up --build
```

- 블로그·운영 UI: **http://127.0.0.1:3847**  
- 운영: **http://127.0.0.1:3847/admin**  
- API: **http://127.0.0.1:8471/health**

Stop / 종료: `docker compose down` (DB 초기화: `docker compose down -v`)

> **macOS / Windows:** use `docker compose.yml` (bridge).  
> **Broken Docker bridge on Linux VM:** `docker compose -f docker-compose.host.yml up --build`

Full troubleshooting: Project store `docs/local-run.md`.

---

## Claude API key

```bash
cp .env.example .env
# Edit .env — never commit secrets:
ANTHROPIC_API_KEY=sk-ant-...
```

| Env | Purpose |
|-----|---------|
| `ANTHROPIC_API_KEY` | Empty → **mock**. Set → live Anthropic |
| `CLAUDE_MODEL_GENERATE` / `_RECOMMEND` | Default `claude-haiku-4-5` |
| `CLAUDE_MODEL_REVIEW` | Default `claude-sonnet-5-5` (~15% or first of batch) |

Key: [Anthropic Console](https://console.anthropic.com/). Restart after change.  
`GET /health` → `"mock_claude": true|false`.

---

## Simple local-dev (no Docker)

```bash
cp .env.example .env
cd apps/api && uv sync
uv run uvicorn autopost_api.main:app --host 0.0.0.0 --port 8471

# other terminal
cd apps/web && npm install && npm run dev
```

---

## Repo layout

```
apps/api/                 FastAPI + Claude + Celery + APScheduler fallback
apps/web/                 Next.js admin + public blog
docker-compose.yml        Laptop-friendly (bridge network)
docker-compose.host.yml   Host-network fallback for restricted Linux VMs
.env.example              Claude key + knobs
```

## Notes

- 발행 채널: 자체 사이트, 티스토리, 구글 블로거. 토큰은 `.env`에만 둡니다. 네이버 블로그 자동 발행은 없습니다.
- GitHub Actions가 한국 시간 오전 9시, 낮 12시, 오후 3시, 오후 6시 구간에 블로거로 글을 한 편씩 발행합니다. 정각 예약은 GitHub가 건너뛰는 경우가 있어, 각 구간에서 11분과 41분에 자동으로 다시 시도합니다. 앞선 시도가 이미 글을 올렸으면 뒤 시도는 넘어갑니다. 워크플로는 저장소 기본 브랜치의 `.github/workflows/seoul-blogger.yml`이며, 키는 Actions 시크릿에만 둡니다. 붙여넣기 파일을 저장소에 올리지 못해도 블로그 발행 자체는 성공으로 남습니다.
- 블로거에 올린 HTML은 `paste/`에도 저장됩니다. 티스토리는 HTML 모드에 붙여넣고, 네이버는 사진과 꾸미기가 빠질 수 있습니다. 이후 발행분도 `paste/`에 추가되고, Actions 실행의 `paste-html` 파일로도 남습니다.  
- AdSense: placeholder slots only.  
- Cloud agent `127.0.0.1` is not your laptop — use a published public URL or Try Live for the agent VM.
