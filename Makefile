DOCKER_COMPOSE ?= docker compose

.PHONY: dev down logs migrate seed reset lint test fmt

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
	$(DOCKER_COMPOSE) run --rm frontend npm run lint
	$(DOCKER_COMPOSE) run --rm backend uv run ruff check

test:
	$(DOCKER_COMPOSE) run --rm frontend npm run test
	$(DOCKER_COMPOSE) run --rm backend uv run pytest

fmt:
	$(DOCKER_COMPOSE) run --rm frontend npm run format
	$(DOCKER_COMPOSE) run --rm backend uv run ruff format
