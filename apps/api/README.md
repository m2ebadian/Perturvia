# Perturvia API

FastAPI backend for Perturvia. Handles agent registration, MCP execution traces, and PostgreSQL persistence.

## Stack

Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, and pytest.

## Running locally

From the repository root:

```bash
docker compose up -d --build
docker compose exec api uv run alembic upgrade head
```

The API runs at `http://localhost:8000`. Interactive API documentation is available at `/docs`.

## Endpoints

- `GET /health` and `GET /health/db` — Health checks
- `POST /agents` — Register an agent
- `GET /agents` — List agents
- `GET /agents/{agent_id}` — Get an agent
- `POST /traces` — Store an MCP tool execution trace
- `GET /traces?run_id=<uuid>` — Retrieve traces for a run

## Testing

Tests use pytest. Database-backed tests require a separate PostgreSQL database and the `TEST_DATABASE_URL` environment variable. The test database name must end in `_test`.

Ruff is used for linting and formatting.
