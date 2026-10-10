# Secure University Attendance System

Project foundation for a university attendance system: a Next.js web application,
an Expo mobile application, and a shared FastAPI backend with PostgreSQL.
The frontends currently contain starter screens; application features and API
integration come later.

See the [technology stack](docs/architecture/README.md) and
[project proposal](docs/Smart_Attendance_Proposal.pdf).

## Prerequisites

- [Git](https://git-scm.com/downloads).
- [Node.js 24](https://nodejs.org/en/download), version 24.3 or newer, with npm.
- [Docker Desktop](https://docs.docker.com/desktop/) running Linux containers.
- [Expo Go compatible with SDK 57](https://expo.dev/go), or an Android emulator / macOS iOS simulator, for mobile preview.

Docker provides Python 3.12 and PostgreSQL 17. A host Python installation,
PostgreSQL installation, or Python virtual environment is not needed.
If using Ubuntu in WSL, enable its integration in Docker Desktop and use that
distro rather than `docker-desktop`. Use one terminal environment per checkout;
run `npm ci` again if switching between Windows and Linux.
In PowerShell, use `npm.cmd` and `npx.cmd` if script execution is blocked.

## Clone and configure

```bash
git clone https://github.com/SecureAttendanceSystem/secure-attendance-system.git
cd secure-attendance-system
git switch sprint
```

When testing an unmerged change, select its branch instead of `sprint`.
On first setup, copy `.env.example` to `.env` **in the repository root**:

```powershell
Copy-Item .env.example .env
```

For Bash, use `cp .env.example .env`. Keep an existing `.env` rather than overwriting it.
Leave `DATABASE_URL` commented out to use your own local PostgreSQL database.

| Variable | Default / purpose |
| --- | --- |
| `DATABASE_URL` | Compose supplies the local database URL when unset |
| `BACKEND_PORT` | `18000`, mapped to container port `8000` |
| `APP_NAME` | `Secure Attendance API` |
| `ENVIRONMENT` | `development`; also accepts `test` or `production` |
| `LOG_LEVEL` | `INFO`; also accepts `DEBUG`, `WARNING`, `ERROR`, `CRITICAL` |
| `CORS_ORIGINS` | JSON array of approved browser origins; defaults to localhost and 127.0.0.1 on port 3000 |

To use Supabase, put its PostgreSQL **session-pooler** URL in the root `.env`, using
this format with your own connection parameters:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres?sslmode=require
```

URL-encode special characters in the password. Plain `postgresql://` URLs also
work. `.env` is ignored by Git; database credentials belong only in the backend
configuration. Web and mobile do not consume API environment variables yet.
Shell environment variables override `.env` when Compose reads settings.

## Run the project

Start Docker Desktop. Run the backend and database from the repository root:

```bash
docker compose up --build -d
docker compose exec backend alembic upgrade head
```

- API documentation: http://localhost:18000/docs
- API health: http://localhost:18000/health
- Database health: http://localhost:18000/health/db

Both health endpoints return `{"status":"ok"}` on success. Alembic applies schema
changes to the database selected by `DATABASE_URL`; use local PostgreSQL for first setup.

In a separate terminal opened at the repository root, start web:

```bash
cd web
npm ci
npm run dev
```

Open http://localhost:3000. In another terminal opened at the root, start mobile:

```bash
cd mobile
npm ci
npm start
```

Scan the QR code with compatible Expo Go on a phone on the same network.
See [mobile setup](mobile/README.md) for emulator instructions.
Each developer runs their own applications; a teammate's PC does not need to stay on.

## Checks and common commands

From the repository root:

```bash
docker compose ps
docker compose exec backend pytest -p no:cacheprovider
docker compose exec backend alembic check
docker compose logs -f backend
```

Stop web/mobile with Ctrl+C. Use `docker compose down` to stop Docker services;
local database data persists. Rebuild with `docker compose up --build -d` after
changing dependencies. After editing `.env`, run
`docker compose up -d --force-recreate backend`.

GitHub Actions runs frontend lint/TypeScript checks, backend tests, Docker builds,
migration checks, and API/database health checks on pull requests to `sprint` or
`main`, pushes to those branches, and manual runs. CI uses a temporary local
database and needs no Supabase secrets. Setup still needs verification by another teammate.

## Repository

```text
backend/            FastAPI, SQLAlchemy, Alembic, and pytest
web/                Next.js and TypeScript
mobile/             React Native, Expo, and TypeScript
database/           Reserved database scripts and seeds
docs/               Technology stack and project proposal
docker-compose.yml  Backend and local PostgreSQL services
.env.example        Shareable backend settings template
```

Alembic migrations live in `backend/alembic/versions/`.
Empty scaffolding folders use `.gitkeep` so Git preserves them.
More commands: [backend](backend/README.md), [web](web/README.md),
[mobile](mobile/README.md), and [contribution workflow](CONTRIBUTING.md).
