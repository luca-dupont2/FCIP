# FCIP — FPGA Compile Intelligence Platform

Local-first experiment tracking, analysis, and prediction for FPGA engineers.

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20.19+ (or 22.12+)
- PostgreSQL 16
- [uv](https://docs.astral.sh/uv/) package manager

### Native Development

```bash
# 1. Bootstrap environment
cp .env.example .env          # edit DATABASE_URL if needed
bash scripts/setup_dev.sh

# 2. Start infrastructure
# Ensure PostgreSQL is running and matches your .env

# 3. Run database migrations
cd packages/backend && alembic upgrade head

# 4. Seed the database (optional — generates synthetic data)
uv run python scripts/create_tables.py
uv run python scripts/generate_synthetic_data.py
uv run python scripts/generate_synthetic_data.py
uv run python scripts/train_models.py

# 5. Start backend
uvicorn fcip_backend.main:app --reload --port 8000

# 6. Start frontend (in another terminal)
cd frontend && npm run dev
```

Open http://localhost:3000 — the frontend proxies `/api` to the backend on port 8000.

### Docker Compose

```bash
docker compose up          # postgres + backend + frontend
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

### CLI

```bash
uv run fcip init                          # initialize project
uv run fcip track <report_dir>            # parse & upload reports
uv run fcip compare <exp_a> <exp_b>       # compare two experiments
uv run fcip predict --device xcvu9p ...   # predict build outcomes
uv run fcip recommend <experiment_id>      # get optimization tips
```

## Project Structure

```
fpga_proj/
├── packages/
│   ├── shared/          # Config, database, models, schemas, exceptions
│   ├── parsers/         # Vivado & Quartus report parsers
│   ├── backend/         # FastAPI REST API
│   ├── cli/             # Typer CLI client
│   ├── predictor/       # ML prediction engine (Random Forest)
│   └── recommender/     # Rule-based recommendation engine
├── frontend/            # Vite + React + Mantine dashboard
├── docker/              # Dockerfiles + nginx config
├── scripts/             # Seed, train, dev setup scripts
├── tests/               # Test fixtures & test suites
└── docs/                # Documentation
```

## Key Design Decisions

- **No auth** for MVP
- **Path + checksum** artifact storage (no file copying)
- **CLI ↔ Backend**: HTTP API only, never direct DB access
- **Git integration**: commit hash + branch + repo name + changed filenames only
- **Prediction**: scikit-learn Random Forest on synthetic data (real data path stubbed)
- **Recommendations**: 12 deterministic rules (R01–R12)
- **Database**: PostgreSQL 16 with JSONB columns, SQLAlchemy 2.0 async
