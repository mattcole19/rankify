## Rankify

Rankify is a lightweight, open-source web app for ranking items within curated categories and comparing personal lists to community sentiment. The goal is to keep the experience fast, opinionated, and production-ready while remaining fun to hack on.

### Repo Layout

- `frontend/` – Vue 3 + TypeScript single-page app served from S3/CloudFront in production.
- `backend/` – FastAPI service powering ranking APIs and aggregation backed by Postgres.
- `infra/` – Pulumi (Python) code provisioning AWS resources (ECS, ALB, RDS, S3, CloudFront, Cognito).
- Root tooling – Makefile, Docker Compose stack, CI configuration, and docs shared across services.

### Development Principles

- One-command local setup via Docker Compose with Bun, FastAPI, and Postgres containers.
- Prefer integration tests and realistic workflows over mocked units when practical.
- Keep secrets out of the repo; use `.env` for local overrides and `.env.example` for documentation.
- Ship narrow slices quickly and refine based on real usage.

### Getting Started

```bash
cp .env.example .env       # tweak ports/DB creds if needed
make dev                   # build and start frontend, backend, postgres
make lint | make test      # run typed lint + unit tests
make migrate               # run Alembic migrations (coming soon)
```

Both the FastAPI service and Vue app expose hot reload when launched through Docker Compose. 

### Tooling

- Install pre-commit hooks (includes `gitleaks` secret scanning):

  ```bash
  pre-commit install
  ```

- GitHub Actions runs lint/test/build for both frontend and backend on every push + PR.
