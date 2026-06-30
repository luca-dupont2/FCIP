# Architecture

## Overview

FCIP is a local-first platform for FPGA engineers to track build experiments, analyze results, and predict outcomes. The system ingests vendor report files (Vivado `.rpt`/`.log`, Quartus `.rpt`/`.log`), parses structured data, and surfaces it through a REST API, CLI, and web dashboard.

```
┌─────────┐   ┌──────────┐   ┌──────────┐
│  CLI    │──▶│ Backend  │──▶│ PostgreSQL│
│ (Typer) │   │ (FastAPI)│   │  (data)   │
└─────────┘   └────┬─────┘   └──────────┘
                    │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
  ┌─────────┐ ┌─────────┐ ┌─────────────┐
  │ Parsers │ │Predictor│ │Recommender  │
  │(Vivado/ │ │ (sklearn│ │ (12 rules)  │
  │ Quartus)│ │  RF)    │ │             │
  └─────────┘ └─────────┘ └─────────────┘
                    │
               ┌────▼────┐
               │Frontend │
               │(React + │
               │Mantine) │
               └─────────┘
```

## Packages

### shared (`fcip_shared`)

Core infrastructure used by all other packages:

- **config** — Pydantic Settings (`AppSettings`) reading from `.env` / env vars
- **database** — SQLAlchemy 2.0 async engine + session factory + `Base` declarative model
- **logging_config** — structlog configuration (JSON or console)
- **exceptions** — `FCIPError` hierarchy (`ParseError`, `NotFoundError`, `PredictionError`, `RecommendationError`, `ImportError`, `InsufficientTrainingDataError`)
- **models/** — 6 ORM models: `Project`, `Experiment`, `Report`, `Artifact`, `Recommendation`, `ModelMetadata`
- **schemas/** — 7 Pydantic V2 schema modules for request/response validation

### parsers (`fcip_parsers`)

Regex-based text parser engine with plugin architecture:

- **VivadoTimingParser** — WNS, TNS, failing paths, critical path
- **VivadoUtilizationParser** — LUT, FF, BRAM, DSP, IO utilization
- **VivadoRuntimeParser** — Synthesis/implementation/bitstream durations from build logs
- **QuartusTimingParser** — Same timing metrics, Quartus format
- **QuartusUtilizationParser** — ALM, registers, M20K, DSP, IO
- **QuartusRuntimeParser** — Stage durations from Quartus log
- **Project detectors** — Auto-detect Vivado/Quartus projects from directory structure
- **Registry** — `get_parser(report_type, tool)` factory

Each parser inherits from `ReportParser` ABC and returns `ParseResult[T]` where T is `TimingResult`, `UtilizationResult`, or `RuntimeResult`. Empty/malformed files return `ParseResult(success=False, errors=[...])`.

### backend (`fcip_backend`)

FastAPI application with 6 routers under `/api/`:

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| projects | `/api/projects` | POST, GET list, GET by id, DELETE |
| experiments | `/api/experiments` | POST, GET list (filtered), GET search (sorted), GET by id, PATCH |
| reports | `/api/reports` | POST, GET by id, GET list (filtered) |
| comparisons | `/api/compare` | POST (2-experiment diff) |
| predictions | `/api/predict` | POST predict, POST /train, GET /models, GET /retrain-status |
| recommendations | `/api/recommend` | POST (evaluate + persist) |

Middleware: CORS (configurable origins), request logging (structlog), centralized `FCIPError` exception handler. Health check at `GET /health`.

### predictor (`fcip_predictor`)

Three scikit-learn Random Forest models with configurable training modes:

| Model | Type | Target |
|-------|------|--------|
| `timing_model.pkl` | RandomForestRegressor | WNS (ns) |
| `runtime_model.pkl` | RandomForestRegressor | compile duration (s) |
| `timing_classifier_model.pkl` | RandomForestClassifier | timing success probability |

Feature vector (~25 columns): device one-hot (5), utilization % (4: LUT/FF/BRAM/DSP), seed, retiming, phys_opt, strategy one-hot (4), + 4 cross-features (`util_product`, `bram_dsp_ratio`, `high_util_flag`, `strategy_perf_flag`). Trained with `n_estimators=100`, `max_depth=15`.

**Training modes** (via `train_all(real_data, data_source)`):
- `data_source="synthetic"` — generates synthetic data only (MVP default)
- `data_source="real"` — trains on user experiment data; requires >= `MIN_REAL_SAMPLES` (50) else raises `InsufficientTrainingDataError` (422)
- `data_source="auto"` (mixed) — uses real data weighted 5:1 over synthetic; falls back to synthetic-only if insufficient real data

**Model registry**: `ModelRegistry` persists `ModelMetadata` rows with `data_source` and `is_active` flags. `deactivate_previous()` marks old models inactive; `register()` writes new model metadata. `Predictor.from_db(db)` loads active models from DB, falling back to file-based loading.

**Feature engineering**: `experiment_to_feature_dict()` converts an Experiment + Report ORM pair to a feature dict. `engineer_features()` adds 4 derived cross-features beyond the raw columns.

### recommender (`fcip_recommender`)

Deterministic rule engine with 12 rules across 4 categories:

- **Timing** (R01–R03): WNS violations, TNS degradation, failing paths
- **Utilization** (R04–R06): LUT/BRAM congestion, DSP saturation
- **Runtime** (R07–R09): Long synthesis, long implementation, bitstream time
- **Strategy** (R10–R12): Retiming suggestion, phys_opt suggestion, seed sweep

Each rule has a `condition` callable and a `message` template. Returns `Recommendation` dataclasses with `rule_name`, `category`, `confidence`, and `message`.

### cli (`fcip_cli`)

Typer CLI that communicates with the backend via HTTP only (never direct DB):

- `init` — Initialize a new FCIP project
- `track` — Parse reports from a directory and upload to backend
- `compare` — Compare two experiments by ID
- `predict` — Run prediction with features or experiment ID
- `recommend` — Get recommendations for an experiment
- `train` — Train or retrain prediction models (synthetic, real, or mixed)
- `dataset-export` — Export experiments as JSONL for sharing/backup
- `dataset-import` — Import experiments from JSONL file
- `model-status` — Show trained model versions and status
- `dataset-export` — Export experiments as JSONL for sharing/backup
- `dataset-import` — Import experiments from JSONL file (team data pooling)

Removed commands (Phase 1 cleanup):
- `upload` — Was a no-op stub, removed
- `watch` — Was just `tail -f`, removed

### frontend

Vite 8 + React 19 + Mantine 9 + TypeScript dashboard:

- 7 pages: Projects, Experiments, Experiment Detail, Compare, Predictions, Recommendations, Settings
- React Router with sidebar navigation
- TanStack Query for API state management
- Recharts for utilization bar charts
- Axios HTTP client with error notification interceptor
- API proxy: `/api` → `http://localhost:8000` in dev

## Data Flow

1. **Ingest**: Engineer runs `fcip track <dir>` → CLI calls parser → POST `/api/experiments` + `/api/reports`
2. **Analyze**: Dashboard shows experiments/reports, comparison endpoints compute metric deltas
3. **Predict**: `POST /api/predict` → Predictor loads `.pkl` models → returns expected WNS, duration, success probability
4. **Recommend**: `POST /api/recommend` → RecommendationEngine evaluates 12 rules → returns ranked recommendations

## Technology Choices

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.12 | ML ecosystem, async support |
| Package manager | uv | Fast, workspace-aware |
| Web framework | FastAPI | Async, OpenAPI docs, dependency injection |
| ORM | SQLAlchemy 2.0 async | Type-annotated, async sessions |
| Database | PostgreSQL 16 | JSON support, UUID, indexes (uses portable `JSON` not `JSONB` for SQLite test compat) |
| Frontend | React + Mantine | Component library, accessible |
| ML | scikit-learn | Robust for tabular, no GPU needed |
| Containerization | Docker Compose | Single-command dev/prod setup |
| Caching | None (Redis removed) | Redis was installed but never used; removed in Phase 1 |
