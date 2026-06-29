# FCIP Project Plan

> Single source of truth for project status, milestones, and roadmap. Any agent or contributor should read this file first.

## Current Status: MVP (M1–M8) + Phase 1 Local Training — Complete

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

- [ ] **Alembic initial migration** — `alembic/versions/` is empty. `alembic upgrade head` is a no-op. Docker entrypoint relies on Alembic, so tables are never created.
  - Fix: Generate initial migration with `alembic revision --autogenerate -m "initial"` (requires running Postgres)
  - Workaround in place: Lifespan event calls `init_db()` on startup, Docker entrypoint also calls `init_db()` before uvicorn
  - Files: `packages/backend/alembic/versions/`

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

## V1 Plan: Real Data via HLSFactory

**Goal**: Replace synthetic training data with real Vivado build results from HLS benchmarks.

**Why**: Synthetic data is acceptable for architecture validation (MVP) but does not generalize for production timing prediction. Real build results capture routing congestion, interconnect effects, and tool heuristics that synthetic generators cannot reproduce.

**Pre-trained models**: None exist publicly. Plunify InTime is commercial (no weights released). AMD/Xilinx and Intel have no public models. HuggingFace has zero FPGA build prediction models. Every DSE paper trains on private data that is never shared.

**Available real data sources**:

| Dataset | Size | Type | Limitation |
|---------|------|------|------------|
| HLSDataset (UT Austin, 2023, arXiv:2302.10977) | ~9K samples/FPGA | HLS synthesis estimates only | No post-impl timing, HLS only |
| HLSFactory (Georgia Tech, 2024, github:sharc-lab/HLSFactory) | PolyBench/MachSuite/CHStone benchmarks | HLS + Vivado runs | Must run builds yourself |
| All other DSE papers | Private, never shared | Varies | Unavailable |

**The hard truth**: No public dataset exists with actual Vivado/Quartus post-implementation results (WNS, TNS, routing utilization, runtime). Every DSE paper generates their own private data. HLSFactory is the closest — it provides the benchmark infrastructure to generate real data.

### V1 Implementation Steps

1. **Install HLSFactory**
   - Add `git+https://github.com/sharc-lab/HLSFactory` to dev dependencies in `pyproject.toml`
   - This framework provides PolyBench, MachSuite, and CHStone benchmark suites with Vivado HLS integration
   - Verify: `uv run python -c "import hlsfactory; print(hlsfactory.__version__)"`

2. **Create `scripts/harvest_hlsfactory.py`**
   - A script that:
     - Clones HLSFactory benchmarks
     - For each benchmark design (5-30 designs):
       - For each directive permutation (inline/no-inline, pipeline/unroll, different loop unroll factors): generate 10-50 permutations per design
       - Runs `vivado_hls` to synthesize each permutation
       - Captures: LUT, FF, BRAM, DSP estimates from HLS synthesis report
       - Saves results as JSON rows: `{benchmark, directive_set, device, lut, ff, bram, dsp, estimated_wns, hls_runtime}`
     - Target: ~1,000-5,000 real samples with a few hours of compute
   - Note: HLS estimates don't include place-and-route timing — that requires V2 (user-supplied full build logs)

3. **~~Add `source` field to `Experiment` model~~** — Done in Phase 1
   - Added `source: Mapped[str] = mapped_column(String(20), default="tracked")` to `packages/shared/fcip_shared/models/experiment.py`
   - Values: `"synthetic"`, `"hlsfactory"`, `"user_upload"`, `"tracked"`
   - No Alembic migration yet (use `init_db()` for now)

4. **~~Extend `ModelTrainer.train_all()` to use real data~~** — Done in Phase 1
   - `train_all(real_data=None, data_source="auto")` — 3 modes: synthetic/real/mixed
   - Real mode requires >=MIN_REAL_SAMPLES (50) experiments, else 422
   - Mixed mode weights real samples 5:1 over synthetic
   - File: `packages/predictor/fcip_predictor/trainer.py`

5. **Add `harvest` CLI command**
   - `fcip harvest --source hlsfactory --benchmark-dir ./benchmarks`
   - Parses resulting reports using existing `VivadoTimingParser` / `VivadoUtilizationParser`
   - Calls `POST /api/experiments` + `POST /api/reports` to ingest results with `source="hlsfactory"`
   - File: `packages/cli/fcip_cli/main.py`

6. **~~Update `scripts/generate_synthetic_data.py`~~** — Done in Phase 1
   - Sets `source="synthetic"` on inserted experiments
   - File: `scripts/generate_synthetic_data.py`

7. **~~Update prediction API to accept data_source~~** — Done in Phase 1
   - `POST /api/predict/train` accepts `ModelTrainRequest` body with `data_source` field
   - `GET /api/predict/retrain-status` returns retrain threshold info
   - `GET /api/predict/models` returns `data_source` and `is_active` fields
   - `ModelRegistry` handles `deactivate_previous()` + `register()` with `data_source`
   - `Predictor.from_db(db)` loads active models from DB, falls back to file-based
   - Files: `packages/backend/fcip_backend/api/predictions.py`, `packages/predictor/fcip_predictor/registry.py`, `packages/predictor/fcip_predictor/predictor.py`

8. **Retrain models with real data**
   - Run `POST /api/predict/train?data_source=hlsfactory`
   - Expect improved accuracy for utilization prediction
   - Timing prediction will still be approximate (HLS estimates, not post-impl)

**Validation criteria**:
- HLSFactory harvest runs to completion
- At least 1,000 real samples in DB
- Models trained on real data show lower MAE than synthetic-only on a held-out test set
- Predictions page shows real model versions in the models list

---

## V2 Plan: User-Supplied Build History (The Moat)

**Goal**: Every FPGA team has private Vivado/Quartus logs. Our tool turns them into training data automatically, creating a flywheel where more usage = better models.

**Why this is the moat**: No pre-trained models exist publicly because FPGA build results are proprietary. Plunify InTime keeps their data closed. By making it trivial for engineers to contribute their build history (while keeping it local-first), FCIP becomes the only tool that improves with use. Each team's private data makes their local models better; optional sharing could eventually create the first public FPGA build prediction dataset.

### V2 Implementation Steps

1. **Extend `fcip track` to auto-train after N new experiments**
   - When experiment count crosses `MODEL_RETRAIN_THRESHOLD` (default: 100, configurable via `.env`), trigger a background retrain using the user's own data
   - Implementation:
     - After successful `track`, query `GET /api/experiments?project_id=X&limit=1` to get total count
     - If count >= threshold, call `POST /api/predict/train?data_source=auto` asynchronously (background task or fire-and-forget)
   - File: `packages/cli/fcip_cli/main.py` (track command)

2. **Create `fcip dataset export` command**
   - Exports all experiments + reports as a JSON Lines file (`.jsonl`)
   - Format per line:
     ```json
     {"experiment": {"id": "...", "tool": "vivado", ...}, "reports": [{"wns": -0.5, ...}], "recommendations": [...]}
     ```
   - Usage: `fcip dataset export --output dataset.jsonl --project my-proj`
   - Enables users to share data if they want to (and for us to receive real data for model improvement)
   - File: `packages/cli/fcip_cli/main.py`

3. **Create `fcip dataset import` command**
   - Import a `.jsonl` file from another FCIP instance
   - Enables team-level data pooling across multiple FCIP instances
   - Usage: `fcip dataset import --input teammate-dataset.jsonl --source user_upload`
   - Sets `source="user_upload"` on imported experiments
   - File: `packages/cli/fcip_cli/main.py`

4. **~~Add `data_source` weighting to `ModelTrainer`~~** — Partially done in Phase 1
   - Mixed training mode already weights real 5:1 over synthetic (`REAL_SAMPLE_WEIGHT=5.0`, `SYNTHETIC_SAMPLE_WEIGHT=1.0`)
   - Still TODO: per-source weight differentiation (hlsfactory 0.5, user_upload 0.8 vs tracked 1.0)
   - File: `packages/predictor/fcip_predictor/trainer.py`

5. **~~Add model versioning and rollback~~** — Partially done in Phase 1
   - Done: `is_active` column on `ModelMetadata`, `ModelRegistry.deactivate_previous()`, `Predictor.from_db(db)` loads active model
   - Still TODO: hold-out evaluation, automatic rollback if new MAE > 1.1 * old MAE
   - Files: `packages/shared/fcip_shared/models/model_metadata.py`, `packages/predictor/fcip_predictor/registry.py`, `packages/predictor/fcip_predictor/predictor.py`

6. **Add per-project model training**
   - Train models per-project when enough data exists (>50 experiments in that project)
   - Rationale: A DSP-heavy design has different timing behavior than an LUT-heavy one. Project-specific models capture these patterns.
   - Implementation:
     - Add `project_id: Mapped[str | None]` column to `ModelMetadata` (nullable — null means "global" model)
     - When `POST /api/predict/train?project_id=X`, train only on that project's experiments
     - `Predictor.predict()` loads project-specific model first, falls back to global model if none exists
   - Files: `packages/shared/fcip_shared/models/model_metadata.py`, `packages/predictor/fcip_predictor/trainer.py`, `packages/predictor/fcip_predictor/predictor.py`, `packages/backend/fcip_backend/api/predictions.py`

7. **Create `fcip model status` CLI command**
   - Shows:
     - Which model versions exist (per project / global)
     - Which is active
     - Last trained timestamp
     - Training data source breakdown (synthetic vs hlsfactory vs user)
     - Accuracy metrics on hold-out set
   - Usage: `fcip model status [--project my-proj]`
   - Calls `GET /api/predict/models` and renders a Rich table
   - File: `packages/cli/fcip_cli/main.py`

8. **Add privacy controls**
   - `fcip config set privacy.data_sharing=off` — ensures data never leaves the local machine
   - When `data_sharing=off`, the `dataset export` command requires explicit `--confirm` flag
   - Store in `.fcip/config.toml` (already created by `fcip init`)
   - Add `privacy` section to `AppSettings` Pydantic config
   - Files: `packages/shared/fcip_shared/config.py`, `packages/cli/fcip_cli/main.py`

9. **Federated learning placeholder** (V3, not V2 — but architecture should support it)
   - For future: aggregate models across multiple FCIP instances without sharing raw data
   - Each site trains locally, then shares only model weight diffs
   - Implementation would use `numpy.diff` on model coefficients or a proper FL framework (Flower, PySyft)
   - For V2, just ensure `ModelMetadata` schema can track `site_id` for future provenance

---

## Test Coverage Summary

### Python Tests (89 total)

| Suite | Count | Location |
|-------|-------|----------|
| Parser unit tests | 20 | `tests/unit/test_parsers/test_all.py` |
| Predictor unit tests | 21 | `tests/unit/test_predictor.py` |
| Registry unit tests | 7 | `tests/unit/test_registry.py` |
| Recommender unit tests | 14 | `tests/unit/test_recommender.py` |
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
uv run pytest tests/ -v                    # all 89 tests
uv run pytest tests/unit/ -v               # unit only (62)
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
