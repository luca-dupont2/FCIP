# Installation Guide

## Prerequisites

| Requirement | Version | Install |
|-------------|---------|---------|
| Python | 3.12+ | [python.org](https://python.org) or `pyenv install 3.12` |
| Node.js | 20.19+ or 22.12+ | [nodejs.org](https://nodejs.org) or `nvm install 22` |
| PostgreSQL | 16 | `brew install postgresql@16` (macOS) or [postgresql.org](https://postgresql.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh | sh` |

## Option A: Native Development

### 1. Clone and configure

```bash
git clone <repo-url> && cd fpga_proj
cp .env.example .env
```

Edit `.env` to match your local PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://fcip:fcip@localhost:5432/fcip
LOG_LEVEL=INFO
LOG_FORMAT=console
CORS_ORIGINS=["http://localhost:5173"]
```

### 2. Create databases

```bash
createdb fcip
# or via psql:
psql -c "CREATE USER fcip WITH PASSWORD 'fcip';"
psql -c "CREATE DATABASE fcip OWNER fcip;"
```

### 3. Install Python dependencies

```bash
uv sync --all-packages
```

### 4. Run database migrations

```bash
cd packages/backend
alembic upgrade head
cd ../..
```

### 5. Seed data (optional)

```bash
uv run python scripts/create_tables.py
uv run python scripts/generate_synthetic_data.py
uv run python scripts/train_models.py
```

### 6. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 7. Start services

```bash
# Terminal 1: Backend
uvicorn fcip_backend.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

### 8. Verify

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## Option B: Docker Compose

```bash
docker compose up
```

This starts:
- `postgres` on port 5432
- `backend` on port 8000 (creates tables and runs Alembic migrations on startup)
- `frontend` on port 5173 (nginx serving built assets, proxying `/api` to backend)

To rebuild after code changes:

```bash
docker compose build --no-cache
docker compose up
```

## CLI Usage

The CLI communicates with the backend over HTTP. Ensure the backend is running first.

```bash
# Initialize a project in the current directory
uv run fcip init

# Parse and upload reports from a build directory
uv run fcip track ./build_reports/

# Compare two experiments
uv run fcip compare <exp-id-a> <exp-id-b>

# Predict outcomes
uv run fcip predict --device xcvu9p-flgb2104-2-e --lut-pct 45 --seed 42

# Get recommendations
uv run fcip recommend <experiment-id>
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://fcip:fcip@localhost:5432/fcip` | PostgreSQL connection string |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FORMAT` | `console` | "console" (human-readable) or "json" (structured) |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `VITE_API_URL` | `/api` | Frontend API base URL |

## Troubleshooting

### Node.js version warnings

Vite 8 requires Node 20.19+. If you see `EBADENGINE` warnings:

```bash
nvm install 22
nvm use 22
```

The project still builds on Node 20.15 with the `@rolldown/binding-darwin-arm64` optional dependency, but upgrading is recommended.

### PostgreSQL connection refused

```bash
# Check PostgreSQL is running
pg_isready

# Check fcip database exists
psql -l | grep fcip
```

### Alembic migration errors

```bash
# Reset all tables (WARNING: destroys data)
cd packages/backend
alembic downgrade base
alembic upgrade head
```

### Frontend build fails

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```
