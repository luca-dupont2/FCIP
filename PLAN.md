# FCIP Project Plan

> Single source of truth for project status, milestones, and roadmap. Any agent or contributor should read this file first.

## Current Status: MVP (M1–M8) + Phase 1 Local Training + V2 User Build History — Complete

### Milestone Summary

| Milestone | Scope | Status |
|-----------|-------|--------|
| M1 | Data model, database, shared package, Alembic setup | Done |
| M2 | Parser engine (Vivado + Quartus, 6 parsers) | Done |
| M3 | CLI collector (init, track, compare, predict, recommend) | Done |
| M4 | Backend API (6 routers, health, CORS, error handling) | Done |
| M5 | Dashboard (7 pages, React+Mantine, TanStack Query, Recharts) | Done |
| M6 | Prediction engine (3 RF models, synthetic generator, feature engineering) | Done |
| M7 | Recommendation engine (12 rules, 4 categories) | Done |
| M8 | Tests, Docker, documentation, performance validation | Done |
| Phase 1 | Local training overhaul (real/mixed/synthetic modes, model registry, retrain threshold) | Done |
| V2 | User build history (auto-retrain, dataset export/import, per-project models, privacy) | Done |

**Note on V1 (HLSFactory)**: Infrastructure exists (`harvest_hlsfactory.py`, `train_on_hlsfactory.py`) but **not recommended for production use**. HLSFactory provides HLS synthesis estimates only — not post-implementation timing. Strategic focus is on **user's own tracked builds** (V2) which provide real production data and form the product moat. HLSFactory scripts retained for testing/demo purposes only.

### Phase 1: Local Training Overhaul (Complete)

12-step implementation replacing synthetic-only training with real/mixed/synthetic modes:

1. `source` column on Experiment ORM + schema (default `"tracked"`)
2. `data_source` + `is_active` columns on ModelMetadata ORM + schema
3. `experiment_to_feature_dict()` helper + 4 derived cross-features (`util_product`, `bram_dsp_ratio`, `high_util_flag`, `strategy_perf_flag`)
4. `InsufficientTrainingDataError` exception registered → 422 in `main.py`
5. `train_all()` rewritten — takes `real_data` tuple + `data_source` param; 3 modes: synthetic/real/mixed with 5:1 sample weighting
6. `ModelRegistry` wired into train endpoint — `deactivate_previous()` + `register()` with `data_source`
7. `Predictor.from_db(db)` async classmethod — loads active models from DB, returns version numbers, falls back to file-based
8. Auto-retrain threshold + `GET /api/predict/retrain-status` endpoint
9. `ModelTrainRequest` has `data_source` field; `ModelTrainResponse` has `data_source` + `is_active`; `ModelMetadataResponse` has both
10. `fcip train` CLI command with `--force` and `--data-source` options
11. Config defaults: `MIN_REAL_SAMPLES=50`, `REAL_SAMPLE_WEIGHT=5.0`, `SYNTHETIC_SAMPLE_WEIGHT=1.0`
12. 21 new tests (89 total, up from 68)

### Test Results (last verified: 2026-06-28)

- **Python**: 89/89 passing (unit + integration + performance) in ~3s
- **Frontend**: 16/16 vitest passing in ~1.2s
- **TypeScript**: zero errors (`tsc -b --noEmit`)
- **Frontend build**: succeeds (`npm run build`)

---

## MVP Completion Checklist

### Must-Fix (MVP will not run end-to-end without these)

- [x] **Alembic initial migration** — `alembic/versions/` is empty. `alembic upgrade head` is a no-op. Docker entrypoint relies on Alembic, so tables are never created.
  - Fix: Generated initial migration with `alembic revision --autogenerate -m "initial"` (requires running Postgres)
  - Applied: `alembic upgrade head` successful
  - Files: `packages/backend/alembic/versions/9054160ad76c_initial.py`

- [x] **Training endpoint doesn't persist ModelMetadata** — Fixed. `POST /api/predict/train` now creates `ModelMetadata` rows for each trained model.
  - Files: `packages/backend/fcip_backend/api/predictions.py`

- [x] **Recommendation `priority` field missing from ORM model + schema** — Fixed. `priority` column added to ORM model, Pydantic schema, and router.
  - Files: `packages/shared/fcip_shared/models/recommendation.py`, `packages/shared/fcip_shared/schemas/recommendation.py`, `packages/backend/fcip_backend/api/recommendations.py`

- [x] **FastAPI lifespan / startup table creation** — Fixed. Lifespan context manager calls `init_db()` on startup and `close_db()` on shutdown.
  - Files: `packages/backend/fcip_backend/main.py`

- [x] **Docker entrypoint must init DB** — Fixed. `backend.sh` now calls `init_db()` via Python before Alembic and uvicorn.
  - Files: `docker/entrypoints/backend.sh`

### Should-Fix (MVP works but has rough edges)

- [x] **`seed_db.py` is misleading** — Fixed. Renamed to `create_tables.py`.
  - Files: `scripts/create_tables.py`

- [x] **`upload` CLI command is a stub** — Fixed. Removed entirely.
  - Files: `packages/cli/fcip_cli/main.py`

- [x] **`watch` CLI command is just `tail -f`** — Fixed. Removed entirely.
  - Files: `packages/cli/fcip_cli/main.py`

- [x] **Redis is a dependency but never used** — Fixed. Removed from deps, docker-compose, config, and .env.example.
  - Files: `packages/shared/pyproject.toml`, `docker-compose.yml`, `packages/shared/fcip_shared/config.py`, `.env.example`

- [x] **Empty `init_cmd.py` / `track_cmd.py`** — Fixed. Deleted both files.
  - Files: (deleted)

---

## Current State (June 30, 2026)

### What's Implemented

**Backend API (6 routers, 33 endpoints)** — All functional:
- `projects` — POST, GET list, GET by id, DELETE
- `experiments` — POST, GET list (filtered), GET search (sorted), GET by id, PATCH
- `reports` — POST, GET by id, GET list (filtered)
- `comparisons` — POST (2-experiment diff)
- `predictions` — POST predict, POST /train, GET /models, GET /retrain-status
- `recommendations` — POST (evaluate + persist 12 rules)

**CLI (9 commands)** — All functional:
`init`, `track`, `compare`, `predict`, `recommend`, `train`, `dataset-export`, `dataset-import`, `model-status`

**Frontend (7 pages, 16 tests)** — All functional:
Projects, Experiments, Experiment Detail, Compare, Predictions, Recommendations, Settings

**ORM Models (7 tables)** — All with correct columns:
`Project`, `Experiment` (with `source`), `Report`, `Artifact`, `Recommendation` (with `priority`), `ModelMetadata` (with `data_source`, `is_active`, `project_id`)

**Alembic** — 1 migration exists (`9054160ad76c_initial.py`)

**Tests** — 95 Python + 16 frontend = 111 total

**Redis** — REMOVED (was dead code — installed but never imported/used)

### Training Pipeline — How Models Are Actually Trained

| Method | Script/Endpoint | Data Source | DB Required | Notes |
|--------|----------------|-------------|-------------|-------|
| Synthetic-only | `scripts/train_models.py` | Synthetic (2000 samples) | No | Default for local dev |
| API training | `POST /api/predict/train` | Configurable (`data_source` param) | Yes (PostgreSQL) | Used by CLI `fcip train`; extracts real data from DB |

**Current state**: Models default to synthetic training. Real data training requires running `fcip track` to ingest user Vivado/Quartus builds. After 50+ builds, auto-retrain on your data produces team-specific models.

**Strategic decision**: HLSFactory infrastructure removed. HLSFactory provides HLS synthesis estimates only — not post-implementation timing. Focus is on **user's own tracked builds** which provide real production data and form the product moat.

### Known Gaps vs. Documented Claims

| Claim | Reality | Status |
|-------|---------|--------|
| "Redis removed" | Now actually removed (was still in config/deps/docker-compose) | ✅ Fixed |
| "89 tests" | Actually 95 tests | ✅ Fixed in docs |
| "Alembic has no migrations" | Migration `9054160ad76c_initial.py` exists | ✅ Fixed in docs |
| "upload/watch commands removed" | Actually removed in Phase 1 | ✅ Fixed in docs |

---

## MVP Status: COMPLETE

All **Must-Fix** and **Should-Fix** items from the original MVP checklist are complete:

- ✅ Alembic initial migration generated and applied
- ✅ Training endpoint persists ModelMetadata to DB
- ✅ Recommendation `priority` field in ORM, schema, and router
- ✅ FastAPI lifespan creates tables on startup
- ✅ Docker entrypoint initializes DB
- ✅ Cleaned up: seed_db.py renamed, upload/watch removed, Redis removed, empty files deleted

**MVP End-to-End Flow Works**:
1. `fcip init` → create project
2. `fcip track <dir>` → parse Vivado/Quartus reports, POST to backend
3. Frontend shows experiments, reports, comparisons
4. `POST /api/predict` → returns WNS, duration, success probability
5. `POST /api/recommend` → returns 12-rule recommendations
6. `fcip train` → trains models (synthetic by default, real if data exists)

**What's NOT in MVP** (V1+ features):
- Background task queue (training is synchronous despite 202 status)
- Per-project models (DB schema supports it, UI needs work)
- Auth/team collaboration (by design — local-first)

---

## Training Strategy

### Recommended Approach: User's Own Builds

**Strategic decision**: Focus on ingesting user's **own Vivado/Quartus build history**.

**Why**:
1. **Real data** — Post-implementation timing (WNS, TNS) from actual builds
2. **Immediate value** — Every FPGA engineer already has build logs; no new tooling required
3. **The moat** — Your team's private data makes your models better; no one else has this data
4. **Low friction** — `fcip track <dir>` works today
5. **Correct problem** — Predicts **your** builds with **your** constraints, **your** device, **your** strategies

### Training Modes

| Method | Data Source | When to Use |
|--------|-------------|-------------|
| `fcip train --data-source=synthetic` | 2000 synthetic samples | Default for new installs, no data yet |
| `fcip train --data-source=auto` (default) | Real (5:1 weight) + synthetic fallback | After 50+ tracked builds; recommended |
| `fcip train --data-source=real` | Real data only | Production use with 100+ builds |

**Flywheel**: Track builds → 50+ experiments → auto-retrain → better predictions → more tracking → even better models.

---

## V2 Plan: User-Supplied Build History (The Moat)

**Goal**: Every FPGA team has private Vivado/Quartus logs. Our tool turns them into training data automatically, creating a flywheel where more usage = better models.

**Why this is the moat**: No pre-trained models exist publicly because FPGA build results are proprietary. Plunify InTime keeps their data closed. By making it trivial for engineers to contribute their build history (while keeping it local-first), FCIP becomes the only tool that improves with use. Each team's private data makes their local models better; optional sharing could eventually create the first public FPGA build prediction dataset.

### V2 Implementation Steps

1. **Extend `fcip track` to auto-train after N new experiments**
   - ✅ After successful `track`, checks retrain status via `GET /api/predict/retrain-status?project_id=X`
   - If threshold reached, calls `POST /api/predict/train?data_source=auto&project_id=X` asynchronously
   - File: `packages/cli/fcip_cli/main.py` (track command)

2. **Create `fcip dataset export` command**
   - ✅ Exports all experiments + reports as a JSON Lines file (`.jsonl`)
   - Format per line:
      ```json
      {"experiment": {"id": "...", "tool": "vivado", ...}, "reports": [{"wns": -0.5, ...}], "recommendations": [...]}
      ```
   - Usage: `fcip dataset export --output dataset.jsonl --project my-proj`
   - Enables users to share data if they want to (and for us to receive real data for model improvement)
   - File: `packages/cli/fcip_cli/main.py`

3. **Create `fcip dataset import` command**
   - ✅ Import a `.jsonl` file from another FCIP instance
   - Enables team-level data pooling across multiple FCIP instances
   - Usage: `fcip dataset import --input teammate-dataset.jsonl --source user_upload`
   - Sets `source="user_upload"` on imported experiments
   - File: `packages/cli/fcip_cli/main.py`

4. **Add `data_source` weighting to `ModelTrainer`**
   - ✅ Per-source weights: tracked=1.0, user_upload=0.8, hlsfactory=0.5, synthetic=1.0
   - File: `packages/predictor/fcip_predictor/trainer.py`

5. **Add per-project model training**
   - ✅ Added `project_id` parameter to train endpoint and `ModelTrainRequest` schema
   - When `POST /api/predict/train?project_id=X`, trains only on that project's experiments
   - `Predictor.from_db(db)` loads project-specific model first, falls back to global model if none exists
   - Files: `packages/backend/fcip_backend/api/predictions.py`, `packages/shared/fcip_shared/schemas/prediction.py`, `packages/predictor/fcip_predictor/trainer.py`, `packages/predictor/fcip_predictor/predictor.py`

6. **Create `fcip model status` CLI command**
   - ✅ Shows model versions, active status, timestamps, data source breakdown, accuracy
   - Usage: `fcip model status [--project my-proj]`
   - Calls `GET /api/predict/models` and renders Rich table
   - File: `packages/cli/fcip_cli/main.py`

7. **Add privacy controls**
   - ✅ `PRIVACY_DATA_SHARING` config setting (default: on)
   - When `data_sharing=off`, `dataset export` requires explicit `--confirm` flag
   - Added to `AppSettings` Pydantic config
   - Files: `packages/shared/fcip_shared/config.py`, `packages/cli/fcip_cli/main.py`

8. **Federated learning placeholder** (V3, not V2 — but architecture should support it)
   - For future: aggregate models across multiple FCIP instances without sharing raw data
   - Each site trains locally, then shares only model weight diffs
   - Implementation would use `numpy.diff` on model coefficients or a proper FL framework (Flower, PySyft)
   - For V2, just ensure `ModelMetadata` schema can track `site_id` for future provenance

---

## Test Coverage Summary

### Python Tests (95 total)

| Suite | Count | Location |
|-------|-------|----------|
| Parser unit tests | 20 | `tests/unit/test_parsers/test_all.py` |
| Predictor unit tests | 21 | `tests/unit/test_predictor.py` |
| Registry unit tests | 7 | `tests/unit/test_registry.py` |
| Recommender unit tests | 14 | `tests/unit/test_recommender.py` |
| Harvest unit tests | 6 | `tests/unit/test_harvest.py` |
| API integration tests | 16 | `tests/integration/test_api.py` |
| Performance tests | 5 | `tests/performance/test_perf.py` |
| E2E tests | 0 (spec written, needs Node 22) | `tests/e2e/spec/dashboard.spec.ts` |

### Frontend Tests (16 total)

| File | Count | Location |
|------|-------|----------|
| DeltaIndicator | 6 | `frontend/src/components/common/__tests__/DeltaIndicator.test.tsx` |
| StatusBadge | 5 | `frontend/src/components/common/__tests__/StatusBadge.test.tsx` |
| Sidebar | 3 | `frontend/src/components/layout/__tests__/Sidebar.test.tsx` |
| App | 1 | `frontend/src/__tests__/App.test.tsx` |
| + 1 precision test | 1 | (in DeltaIndicator file) |

### Commands

```bash
# Python tests
uv run pytest tests/ -v                    # all 95 tests
uv run pytest tests/unit/ -v               # unit only (79)
uv run pytest tests/integration/ -v        # integration only (16)
uv run pytest tests/performance/ -v        # performance only (5)

# Frontend tests
cd frontend && npm test                    # all 16 vitest tests

# Type checking
cd frontend && npx tsc -b --noEmit         # zero errors expected

# Frontend build
cd frontend && npm run build               # should succeed
```

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| No pre-trained models | Train our own | None exist publicly; Plunify InTime is closed-source |
| Synthetic data for MVP | Acceptable for pipeline validation | Cannot capture real routing/congestion; sufficient for architecture proof |
| Real data path | HLSFactory for V1, user builds for V2 | Only available source of real Vivado results |
| PostgreSQL-only types removed | JSON + Uuid (portable) | Tests use SQLite in-memory; JSONB/UUID(pg) broke test compat |
| CLI ↔ Backend | HTTP API only | Never direct DB; enables separate deployment |
| No auth | MVP scope | Local-first, single-user |
| Artifact storage | Path + checksum only | No file copying; just reference |
| 3 RF models | timing regressor, runtime regressor, timing classifier | Answers the 3 practical engineer questions |
| Real data strict mode | 422 if <50 real samples when `data_source="real"` | Never silently fall back to synthetic |
| Mixed training weights | real 5:1 over synthetic | At 50 real + 2000 synthetic, effective ratio 250:2000 |
| `MIN_REAL_SAMPLES=50` | Compromise between 20 (too few for RF) and 100 (too long to reach) | Fewer samples = unreliable RF |
| Federation architecture | Standalone aggregation server, internal sklearn tree arrays | Separation of concerns, 100x smaller payload, DP-noise compatible |
| Redis removed | Dead code — installed but never used | No caching layer implemented; removed from deps, config, docker-compose |

---

## Known Limitations

- **Node version**: Frontend requires Node >=20.19 (Vite 8). Current dev machine is 20.15. Works with `@rolldown/binding-darwin-arm64` polyfill but Node 22 recommended.
- **Playwright E2E**: Specs written but can't run (need Node 22 + running dev server)
- **Docker build**: Dockerfiles verified logically but can't test (no Docker daemon on dev machine)
- **NumPy warning**: `Setting shape on NumPy array has been deprecated in NumPy 2.5` — from joblib, filtered in `pyproject.toml`
- **Quartus runtime parser**: Fixed in Phase 1 — removed wall-clock timestamp patterns
- **Vivado runtime parser**: `bitstream_duration` sometimes None due to log format mismatch — acceptable for MVP
- **Backend API logic**: Inline in routers (services dir has empty `__init__.py` stubs) — acceptable for MVP, refactor to services layer in V1
- **Parser `base.py`**: `ParseResult` Generic type hint uses `TypeVar("T")` inline — may cause type checking issues but works at runtime
- **Training is synchronous**: `POST /api/predict/train` returns 202 but runs synchronously — no background tasks yet
- **Model training default**: `scripts/train_models.py` trains with synthetic data only (no DB); real data training requires API endpoint or `fcip track` to ingest user builds
