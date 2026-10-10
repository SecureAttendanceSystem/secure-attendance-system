# Technology stack

| Component | Technology |
| --- | --- |
| Web | React, Next.js, TypeScript |
| Mobile | React Native, Expo, TypeScript |
| Backend | Python, FastAPI, Uvicorn |
| API | REST with JSON requests and responses |
| Database | PostgreSQL; local Docker database or Supabase hosting |
| ORM and driver | SQLAlchemy, Psycopg 3 |
| Migrations | Alembic |
| Development environment | Docker, Docker Compose, Node.js 24 |
| Checks | Pytest, ESLint, TypeScript |
| CI | GitHub Actions |
| Collaboration | Git, GitHub, Linear |

Web and mobile will call the same FastAPI backend. The backend owns database
access and application rules. The frontend starters are not connected to it yet.
Authentication has not been selected. Attendance verification methods will be
evaluated in a later iteration.

See [project setup](../../README.md) for installation and startup instructions.
