DOCKER_COMPOSE ?= docker compose

.PHONY: dev down logs migrate seed reset lint test fmt verify backend-dev-deps

dev:
	$(DOCKER_COMPOSE) up --build

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

migrate:
	$(DOCKER_COMPOSE) run --rm backend uv run alembic upgrade head

seed:
	$(DOCKER_COMPOSE) run --rm backend uv run python -m rankify.seed

reset:
	$(DOCKER_COMPOSE) down -v || true
	$(DOCKER_COMPOSE) up --build -d
	$(DOCKER_COMPOSE) run --rm backend uv run alembic upgrade head
	$(DOCKER_COMPOSE) run --rm backend uv run python -m rankify.seed

lint:
	$(DOCKER_COMPOSE) run --rm frontend sh -c "npm install && npm run lint"
	$(DOCKER_COMPOSE) run --rm backend uv sync --extra dev
	$(DOCKER_COMPOSE) run --rm backend uv run ruff check

test:
	$(DOCKER_COMPOSE) run --rm frontend sh -c "npm install && npm run test"
	$(DOCKER_COMPOSE) run --rm backend uv sync --extra dev
	$(DOCKER_COMPOSE) run --rm backend uv run pytest

fmt:
	$(DOCKER_COMPOSE) run --rm frontend npm run format
	$(DOCKER_COMPOSE) run --rm backend uv run ruff format

verify:
	$(DOCKER_COMPOSE) build
	$(DOCKER_COMPOSE) run --rm frontend sh -c "npm install && npm run lint"
	$(DOCKER_COMPOSE) run --rm frontend sh -c "npm install && npm run test"
	$(DOCKER_COMPOSE) run --rm frontend sh -c "npm install && npm run build"
	$(DOCKER_COMPOSE) run --rm backend uv sync --extra dev
	$(DOCKER_COMPOSE) run --rm backend uv run ruff check
	$(DOCKER_COMPOSE) run --rm backend uv run pytest

backend-local:
	cd backend && uv run uvicorn rankify.main:app --host 0.0.0.0 --port $${BACKEND_PORT:-8000} --reload
