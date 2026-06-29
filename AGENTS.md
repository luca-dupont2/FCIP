# AGENTS.md

> Instructions for AI agents working on this project. Read this before making any changes.

## Project Overview

FCIP (FPGA Compile Intelligence Platform) — a local-first experiment tracking, analysis, and prediction platform for FPGA engineers.

- **Stack**: Python 3.12 + FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 (backend), Vite 8 + React 19 + Mantine 9 + TypeScript (frontend), scikit-learn (ML), Typer + Rich (CLI)
- **Package manager**: `uv` workspace monorepo for Python, `npm` for frontend
- **Full plan**: See `PLAN.md` for milestones, roadmap, and MVP completion checklist
- **Known bugs**: See `docs/known_issues.md` for tracked issues and fixes

## Commands to Run

### Python Tests (MUST run after any Python change)

```bash
uv run pytest tests/ -v              # all 68 tests
uv run pytest tests/unit/ -v         # unit only
uv run pytest tests/integration/ -v  # integration only
uv run pytest tests/performance/ -v  # performance benchmarks
```

Tests use SQLite in-memory via `aiosqlite` (no external services needed). All tests should pass in ~3s.

### Frontend Tests (MUST run after any frontend change)

```bash
cd frontend && npm test              # all 16 vitest tests (uses happy-dom)
```

### Frontend Type Check (MUST run after any TypeScript change)

```bash
cd frontend && npx tsc -b --noEmit   # must exit with zero errors
```

### Frontend Build

```bash
cd frontend && npm run build         # must succeed
```

### Frontend Lint

```bash
cd frontend && npm run lint          # oxlint (note: broken on Node 20.15 due to native binding)
```

Oxlint has a known native binding issue on Node 20.15. It works on Node 22+. Do not treat oxlint failures as blockers on this Node version.

### Model Training

```bash
uv run python scripts/train_models.py [N_SAMPLES]   # default 2000
```

Generates `.pkl` model files in `packages/predictor/models/`.

### Database Setup

```bash
uv run python scripts/create_tables.py               # creates tables (no data)
uv run python scripts/generate_synthetic_data.py    # inserts synthetic data
```

### Backend Start

```bash
uvicorn fcip_backend.main:app --reload --port 8000
```

### Frontend Dev Server

```bash
cd frontend && npm run dev
```

Requires Node >=20.19 (Vite 8 constraint). Proxy: `/api` → `http://localhost:8000`.

## Code Conventions

### Python

- **Formatting**: Follow PEP 8. No enforced formatter — match surrounding code style.
- **Imports**: `from __future__ import annotations` at top of every file. Grouped: stdlib, third-party, local. Use explicit imports (no wildcard except in `__init__.py` for re-exports).
- **Types**: Full type annotations on all function signatures. Use `Mapped[...]` for SQLAlchemy columns. Use `|` union syntax (Python 3.12+).
- **Async**: All DB operations are async. Use `AsyncSession`, `async_sessionmaker`, `create_async_engine`.
- **Models**: Inherit from `Base` (imported from `fcip_shared.database`). Use `Mapped` + `mapped_column`. Do NOT use PostgreSQL-specific types (`JSONB`, `UUID` from `sqlalchemy.dialects.postgresql`) — use portable `JSON` and `Uuid` from `sqlalchemy` core instead. Tests use SQLite in-memory which doesn't support PostgreSQL dialect types.
- **Schemas**: Pydantic V2 with `model_config = {"from_attributes": True}` for ORM mode.
- **Exceptions**: Raise `FCIPError` subclasses from `fcip_shared.exceptions` — they are caught by the centralized error handler.
- **No comments in code** unless explicitly requested. Code should be self-documenting.
- **No secrets/keys** ever committed. `.env` is gitignored.

### TypeScript / React

- **Formatting**: No enforced formatter. Match existing file style.
- **Imports**: Group by external → local. Use `@/` path alias for `src/`.
- **Components**: Functional components with explicit prop interfaces. Use Mantine components, do not reinvent UI primitives.
- **State management**: TanStack Query for server state. Local state via React hooks only.
- **API calls**: Use hooks in `src/api/` directory. Axios client with interceptors in `src/api/client.ts`.
- **No comments in code** unless explicitly requested.
- **Tests**: Use `happy-dom` environment (not `jsdom`). Render with `MantineProvider` wrapper.

### Project Structure

```
fpga_proj/
├── packages/
│   ├── shared/        # fcip_shared — config, database, models, schemas, exceptions
│   ├── parsers/       # fcip_parsers — Vivado + Quartus report parsers
│   ├── backend/       # fcip_backend — FastAPI REST API
│   ├── cli/           # fcip_cli — Typer CLI client
│   ├── predictor/     # fcip_predictor — ML prediction engine
│   └── recommender/   # fcip_recommender — Rule-based recommendation engine
├── frontend/          # Vite + React + Mantine dashboard
├── docker/            # Dockerfiles + nginx config + entrypoints
├── scripts/           # Seed, train, dev setup scripts
├── tests/             # Python test suites (unit, integration, performance, e2e)
├── docs/              # Architecture, API reference, DB schema, known issues
├── PLAN.md            # Full project plan and roadmap
└── pyproject.toml     # uv workspace root config
```

## Key Files to Know

| Purpose | File |
|---------|------|
| Project plan & roadmap | `PLAN.md` |
| Known bugs & fixes | `docs/known_issues.md` |
| Architecture doc | `docs/architecture.md` |
| API reference | `docs/api_reference.md` |
| Database schema | `docs/database_schema.md` |
| Environment variables | `.env.example` |
| Python test config | `pyproject.toml` (pytest section) |
| Frontend test config | `frontend/vite.config.ts` (test section) |
| Frontend tsconfig | `frontend/tsconfig.app.json` |
| Docker compose | `docker-compose.yml` |
| Alembic config | `packages/backend/alembic.ini` |

## Common Pitfalls

1. **Circular imports**: `fcip_shared.database` and `fcip_shared.models` have a circular dependency. Models import `Base` from database. Database must NOT import models at module level. Model registration for `Base.metadata` happens via `import fcip_shared.models` inside `init_db()` only. Never add `import fcip_shared.models` at module level in `database.py`.

2. **PostgreSQL-only types break tests**: Tests use SQLite in-memory. Never use `JSONB` (use `JSON`), never use `UUID` from `sqlalchemy.dialects.postgresql` (use `Uuid` from `sqlalchemy` core). If you add a new model column, verify it works with SQLite.

3. **Node version**: Frontend requires Node >=20.19 (Vite 8). Our dev machine is 20.15. Works with `@rolldown/binding-darwin-arm64` polyfill but some tools (oxlint, E2E tests) break. Node 22 recommended.

4. **Alembic has no migrations**: The `alembic/versions/` directory is empty. Do not rely on `alembic upgrade head` to create tables. Use `init_db()` — the lifespan event calls it automatically on startup.

5. **`train_all()` ignores the db_session argument**: The `ModelTrainer.train_all()` method accepts `db_session` but always uses synthetic data. Do not pass a DB session expecting it to train on real data — that feature doesn't exist yet (planned for V1).

6. ~~**Recommendation ORM model is missing `priority` column**~~: Fixed — `priority` column added to ORM model, schema, and router.

## Before Committing

1. Run `uv run pytest tests/ -v` — must pass (68 tests)
2. Run `cd frontend && npm test` — must pass (16 tests)
3. Run `cd frontend && npx tsc -b --noEmit` — must exit with zero errors
4. Never commit `.env`, `.pkl` model files, or secrets
5. Check `git status` and `git diff` before staging — only stage intended files
6. Write concise commit messages matching existing style (imperative mood, no emoji)
