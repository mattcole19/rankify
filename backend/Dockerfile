# syntax=docker/dockerfile:1.7

FROM python:3.13-slim AS base

ENV UV_PROJECT_ENV=/app/.venv \
    PATH="/usr/local/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh -s -- --yes --no-modify-path \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && rm -rf /root/.local

WORKDIR /app

FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

FROM base AS dev
ENV PYTHONUNBUFFERED=1
COPY --from=deps /app/.venv /app/.venv
COPY . .
CMD [
  "uv",
  "run",
  "uvicorn",
  "rankify.main:app",
  "--host",
  "0.0.0.0",
  "--port",
  "8000",
  "--reload"
]

FROM base AS prod
ENV PYTHONUNBUFFERED=1
COPY --from=deps /app/.venv /app/.venv
COPY . .
CMD ["uv", "run", "uvicorn", "rankify.main:app", "--host", "0.0.0.0", "--port", "8000"]
