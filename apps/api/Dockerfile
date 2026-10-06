FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md ./
COPY apps/api/src ./src

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 8471

CMD ["uvicorn", "autopost_api.main:app", "--host", "0.0.0.0", "--port", "8471"]
