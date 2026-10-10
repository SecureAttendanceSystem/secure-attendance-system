# Backend

Python 3.12, FastAPI, SQLAlchemy, Psycopg 3, and Alembic. Docker installs the
dependencies; no local Python virtual environment is needed.
Configure the root `.env` using the [project setup](../README.md).

## Run

From the repository root:

```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

- http://localhost:18000/docs — interactive API documentation
- http://localhost:18000/health — API health
- http://localhost:18000/health/db — database connectivity

Both health endpoints return `{"status":"ok"}` on success. The database check
uses `SELECT 1` and returns HTTP 503 if the connection fails.
Python edits reload automatically. Rebuild after dependency changes.

```bash
docker compose logs -f backend
docker compose down
```

The local PostgreSQL port is internal to Docker. Open its SQL shell with:

```bash
docker compose exec db psql -U attendance -d attendance
```

## Tests and migrations

```bash
docker compose exec backend pytest -p no:cacheprovider
docker compose exec backend alembic check
```

Tests cover health, settings, CORS, and exception handling without contacting
a real database. CI tests migrations on its own temporary PostgreSQL database.

After changing database models, create and review a migration:

```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
docker compose exec backend alembic upgrade head
```

Migration commands target the configured database. Coordinate schema changes
before running them against a shared Supabase project.

## Structure

```text
app/main.py       Application setup, middleware, and lifespan
app/api/          APIRouter and endpoint modules
app/core/         Settings, exception handlers, and logging
app/database/     SQLAlchemy engine and model base
app/models/       Database models
app/schemas/      Reserved request and response models
app/services/     Reserved application operations
app/security/     Reserved authentication helpers
alembic/          Migration configuration and revisions
tests/            Backend foundation tests
```

Register new route modules in `app/api/router.py`. Settings are supplied by
Compose, including explicit browser origins for CORS. Errors use JSON `detail`;
unexpected errors return a generic HTTP 500 response.
