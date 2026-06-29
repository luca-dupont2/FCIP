# Known Issues

> Tracked bugs, defects, and rough edges. Organized by severity.

## Critical (MVP will not run end-to-end)

### KI-001: Alembic has zero migration files

**Status**: Open (workaround in place — lifespan event creates tables on startup)
**Severity**: Critical
**Affected files**: `packages/backend/alembic/versions/` (empty directory)
**Impact**: `alembic upgrade head` is a no-op. Docker entrypoint runs `alembic upgrade head` before starting uvicorn, so tables are never created in Docker deployments. All API calls fail with database errors.

**Root cause**: Initial migration was never generated.

**Fix**:
1. Start a running Postgres instance matching `.env` config
2. Run `cd packages/backend && alembic revision --autogenerate -m "initial"`
3. Verify the generated migration includes all 6 tables (projects, experiments, reports, artifacts, recommendations, model_metadata) and all indexes
4. Commit the migration file

**Alternative fix**: Add a FastAPI lifespan event that calls `init_db()` on startup — this makes the backend self-healing regardless of Alembic state. Both approaches (lifespan + migrations) should coexist.

---

### KI-002: Training endpoint doesn't persist ModelMetadata to DB

**Status**: Fixed (rewritten in Phase 1)
**Severity**: Critical
**Affected files**: `packages/backend/fcip_backend/api/predictions.py`

**Impact** (original): `POST /api/predict/train` trained models and saved `.pkl` files but never wrote `ModelMetadata` rows to the database.

**Fix** (Phase 1): Complete rewrite of train endpoint:
- Uses `ModelRegistry` to `deactivate_previous()` + `register()` with `data_source`
- `train_all()` now takes `real_data` tuple + `data_source` param (not `db_session`)
- Endpoint extracts real data via `_extract_real_training_data(db)` helper
- Returns `data_source` + `is_active` in response

---

### KI-003: Recommendation `priority` field missing from ORM + schema

**Status**: Fixed
**Severity**: Critical (data loss)
**Affected files**:
- `packages/shared/fcip_shared/models/recommendation.py` — no `priority` column
- `packages/shared/fcip_shared/schemas/recommendation.py` — no `priority` field
- `packages/backend/fcip_backend/api/recommendations.py:43-49` — `priority` is silently dropped

**Impact**: The recommender engine produces `Recommendation` dataclasses with `priority` (HIGH/MEDIUM/LOW). The frontend type definition expects `priority: string`. But:
1. The ORM `Recommendation` model has no `priority` column, so it can't be stored
2. The Pydantic `RecommendationResponse` schema has no `priority` field, so it's not returned by the API
3. The router creates DB records without passing `priority`

**Fix**:
1. Add to ORM model (`recommendation.py`):
   ```python
   priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
   ```
2. Add to Pydantic schema (`schemas/recommendation.py`):
   ```python
   priority: str | None = None
   ```
3. Update router (`api/recommendations.py`):
   ```python
   db_rec = Recommendation(
       experiment_id=body.experiment_id,
       rule_name=rec.rule_name,
       category=rec.category,
       priority=rec.priority.value if rec.priority else None,
       message=rec.message,
       confidence=rec.confidence,
   )
   ```
4. Generate Alembic migration for the new column

---

### KI-004: No FastAPI lifespan event to create tables on startup

**Status**: Fixed
**Severity**: Critical (for fresh deployments)
**Affected files**: `packages/backend/fcip_backend/main.py`
**Impact**: Starting the backend against a fresh database (no tables, no Alembic migrations) produces a running server where every API call fails. The only way to create tables is to manually run `scripts/seed_db.py` or `init_db()` before starting.

**Root cause**: No startup/lifespan hook exists. Tables are only created by explicit calls to `init_db()` or `alembic upgrade head`, neither of which happens automatically.

**Fix**: Add a lifespan context manager to `main.py`:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from fcip_shared.database import init_db
    await init_db()
    yield
    from fcip_shared.database import close_db
    await close_db()

# In create_app():
app = FastAPI(..., lifespan=lifespan)
```

This ensures tables are created (via `create_all`) on every startup. Safe to call repeatedly — `create_all` is idempotent for existing tables.

---

### KI-005: Docker entrypoint doesn't create tables

**Status**: Fixed
**Severity**: Critical (Docker deployments fail)
**Affected files**: `docker/entrypoints/backend.sh`
**Impact**: `backend.sh` runs `alembic upgrade head` (no-op with empty versions/) then starts uvicorn. Tables never get created. All API calls in Docker fail.

**Fix**: Add explicit table creation before uvicorn:
```bash
#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "Ensuring database tables exist..."
python -c "from fcip_shared.database import init_db; import asyncio; asyncio.run(init_db())"

echo "Running database migrations..."
alembic upgrade head || echo "Migration note: will retry on next start"

echo "Starting FCIP backend..."
exec uvicorn fcip_backend.main:app --host 0.0.0.0 --port 8000
```

---

## Medium (MVP works but with rough edges)

### KI-006: `seed_db.py` is misleadingly named

**Status**: Fixed — renamed to `create_tables.py`
**Severity**: Low
**Affected files**: `scripts/seed_db.py`
**Impact**: Name implies data seeding but it only creates the schema (calls `init_db()`). Running `seed_db.py` produces an empty database. Users must also run `generate_synthetic_data.py` to get actual data.

**Fix**: Rename to `create_tables.py` or merge with `generate_synthetic_data.py` into a single `scripts/demo_setup.py`.

---

### KI-007: `upload` CLI command is a no-op stub

**Status**: Fixed — removed
**Severity**: Low
**Affected files**: `packages/cli/fcip_cli/main.py`
**Impact**: User runs `fcip upload` and gets a message saying "Running track again is recommended." No functionality.

**Fix options**:
- A) Implement: `upload` re-runs track on a previously-initialized directory with `--force` to update existing experiments
- B) Remove: Delete the command entirely, keep `track` as the single ingestion point
- C) Repurpose: Make `upload` accept a `.jsonl` dataset file (aligns with V2 `dataset import`)

---

### KI-008: `watch` CLI command is just `tail -f`

**Status**: Fixed — removed
**Severity**: Low
**Affected files**: `packages/cli/fcip_cli/main.py`
**Impact**: `watch` finds the latest `.log` file and tails it line-by-line. No parsing, no progress detection, no backend integration.

**Fix options**:
- A) Implement minimal version: Parse progress lines (e.g., Vivado "% complete" messages), update experiment status via API
- B) Remove until V1: Placeholder UI with `--coming-soon` message
- C) Use filesystem watcher: Watch a directory for new `.rpt` files, auto-track them when they appear

---

### KI-009: Redis is declared but never used

**Status**: Fixed — removed from deps, docker-compose, config, and .env.example
**Severity**: Low
**Affected files**: `packages/shared/pyproject.toml`, `docker-compose.yml`
**Impact**: `redis[hiredis]>=5.0` is installed and `REDIS_URL` configured, but no code reads from or writes to Redis. No caching layer exists. Wasted container resource in Docker.

**Fix options**:
- A) Add minimal caching: Cache `/api/predict/models` results with 60s TTL. Use `redis.asyncio` in a new `packages/shared/fcip_shared/cache.py` module.
- B) Remove for MVP: Drop `redis` from deps and docker-compose.yml. Add back in V1 when actual caching is needed.

---

### KI-010: Dead code files (`init_cmd.py`, `track_cmd.py`)

**Status**: Fixed — deleted
**Severity**: Trivial
**Affected files**: `packages/cli/fcip_cli/init_cmd.py`, `packages/cli/fcip_cli/track_cmd.py`
**Impact**: Empty files. All CLI logic is in `main.py`.

**Fix**: Delete both files.

---

## Low (Cosmetic / Future)

### KI-011: NumPy 2.5 deprecation warning in joblib

**Status**: Open (upstream)
**Severity**: Trivial
**Impact**: ~1000 warnings during pytest runs: `Setting the shape on a NumPy array has been deprecated in NumPy 2.5`
**Root cause**: joblib's `numpy_pickle.py:207` sets `array.shape` directly. Fixed in joblib upstream (pending release).
**Fix**: Wait for joblib release, or filter warnings in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
filterwarnings = ["ignore::DeprecationWarning:joblib"]
```

### KI-012: Quartus runtime parser returns suspicious values

**Status**: Fixed — removed wall-clock timestamp patterns that were treated as durations
**Severity**: Low
**Affected files**: `packages/parsers/fcip_quartus/timing.py` (QuartusRuntimeParser)
**Impact** (original): For a 45-minute log, parser returned `synth=31500s` (8.75 hours). Wall-clock timestamps were treated as durations.
**Fix**: Removed patterns matching absolute timestamps; only duration patterns are now recognized.

### KI-013: Vivado runtime parser bitstream_duration sometimes None

**Status**: Open
**Severity**: Low
**Affected files**: `packages/parsers/fcip_vivado/timing.py` (VivadoRuntimeParser)
**Impact**: `bitstream_duration` returns None when log format doesn't match the expected "write_bitstream completed" pattern.
**Acceptable for MVP**: Not all Vivado logs include bitstream generation.

### KI-014: Backend API logic is inline in routers

**Status**: Open (by design for MVP)
**Severity**: Architectural
**Affected files**: `packages/backend/fcip_backend/api/*.py`, `packages/backend/fcip_backend/services/__init__.py` (empty)
**Impact**: All CRUD logic lives directly in router handler functions. The `services/` directory exists but is empty. Makes testing and reuse harder.
**Fix in V1**: Extract service layer. Each router calls a service function. Services are injectable for testing. Pattern: `router.py` → `services/project_service.py`.

### KI-015: `train_all()` no longer accepts `db_session` parameter

**Status**: Open (breaking change from Phase 1)
**Severity**: Low (internal API only)
**Affected files**: `packages/predictor/fcip_predictor/trainer.py`
**Impact**: `train_all()` signature changed from `train_all(db_session=None)` to `train_all(real_data=None, data_source="auto")`. Any code passing a DB session directly to `train_all()` will fail. The predictions endpoint now extracts real data via `_extract_real_training_data(db)` before calling `train_all()`.
**Migration**: Callers must extract real training data from DB first, then pass it as `(X, y_timing, y_runtime, y_classify)` tuple to `real_data`.

### KI-016: Training is synchronous despite 202 status code

**Status**: Open
**Severity**: Low
**Affected files**: `packages/backend/fcip_backend/api/predictions.py`
**Impact**: `POST /api/predict/train` returns HTTP 202 (Accepted) but the training runs synchronously in the request handler. The response is blocked until training completes (~1-5s for synthetic, longer for real data). Background tasks would be more appropriate for the 202 semantics.
**Fix in V1**: Use FastAPI `BackgroundTasks` or a task queue to run training asynchronously. Return a task ID that can be polled for completion.
