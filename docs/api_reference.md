# API Reference

Base URL: `http://localhost:8000`

Interactive docs: `GET /docs` (Swagger UI) | `GET /redoc` (ReDoc)

---

## Health

### `GET /health`

Returns service health status.

**Response**: `200`

```json
{ "status": "ok" }
```

---

## Projects

### `POST /api/projects`

Create a new project.

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Project name (unique) |
| path | string | no | Filesystem path |
| description | string | no | Project description |

**Response**: `201`

```json
{
  "id": "uuid",
  "name": "my-fpga-design",
  "path": "/home/user/project",
  "description": "Top-level FPGA design",
  "experiment_count": 0,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

### `GET /api/projects`

List all projects.

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| limit | int | 50 | Max results (1–200) |
| offset | int | 0 | Results offset |

**Response**: `200` — Array of `ProjectResponse`

### `GET /api/projects/{project_id}`

Get a single project by ID.

**Response**: `200` — `ProjectResponse` | `404` if not found

### `DELETE /api/projects/{project_id}`

Delete a project and all its experiments (cascade).

**Response**: `204` | `404` if not found

---

## Experiments

### `POST /api/experiments`

Create an experiment.

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| project_id | string (UUID) | yes | Parent project |
| name | string | no | Human-readable name |
| tool | string | yes | "vivado" or "quartus" |
| tool_version | string | no | e.g. "2024.1" |
| device | string | no | Target FPGA part |
| seed | int | no | Implementation seed |
| status | string | no | "running", "success", "failed", "timeout" |
| git_commit | string | no | 40-char SHA |
| branch | string | no | Git branch |
| repository_name | string | no | Repo name |
| compile_options | object | no | Strategy, retiming, phys_opt, etc. |
| machine_info | object | no | CPU, RAM, OS |
| changed_files | string[] | no | List of changed filenames |
| completed_at | string (datetime) | no | Completion timestamp |

**Response**: `201` — `ExperimentResponse`

### `GET /api/experiments`

List experiments with filters.

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| project_id | string | — | Filter by project |
| tool | string | — | Filter by tool ("vivado"/"quartus") |
| status | string | — | Filter by status |
| branch | string | — | Filter by branch |
| seed | int | — | Filter by seed |
| limit | int | 50 | Max results (1–200) |
| offset | int | 0 | Results offset |

**Response**: `200`

```json
{
  "items": [ExperimentResponse, ...],
  "total": 142,
  "limit": 50,
  "offset": 0
}
```

### `GET /api/experiments/search`

Search and sort experiments.

**Query Parameters**:

All list filters plus:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| q | string | "" | Natural language query (e.g. "best wns") |
| min_wns | float | — | Minimum WNS filter |
| max_wns | float | — | Maximum WNS filter |
| sort_by | string | "created_at:desc" | Sort field:direction |

Recognized `q` hints: `"best wns"` → WNS ascending, `"worst wns"` → WNS descending.

**Response**: `200` — `ExperimentListResponse`

### `GET /api/experiments/{experiment_id}`

Get a single experiment.

**Response**: `200` — `ExperimentResponse` | `404`

### `PATCH /api/experiments/{experiment_id}`

Partially update an experiment.

**Request Body** (partial):

| Field | Type | Description |
|-------|------|-------------|
| name | string | New name |
| status | string | New status |
| completed_at | string | Completion time |

**Response**: `200` — `ExperimentResponse` | `404`

---

## Reports

### `POST /api/reports`

Create a parsed report.

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| experiment_id | string (UUID) | yes | Parent experiment |
| report_type | string | yes | "timing", "utilization", "runtime" |
| wns | float | no | Worst Negative Slack |
| tns | float | no | Total Negative Slack |
| failing_paths | int | no | Number of failing paths |
| critical_path | string | no | Critical path description |
| lut / lut_available | int | no | LUT usage / available |
| ff / ff_available | int | no | FF usage / available |
| bram / bram_available | int | no | BRAM usage / available |
| dsp / dsp_available | int | no | DSP usage / available |
| io_used / io_available | int | no | IO usage / available |
| clock_utilization | float | no | Clock utilization % |
| synthesis_duration | float | no | Synthesis time (seconds) |
| implementation_duration | float | no | Implementation time (seconds) |
| bitstream_duration | float | no | Bitstream generation time (seconds) |
| total_runtime | float | no | Total build time (seconds) |
| raw_content | string | no | Original report text |
| source_file | string | no | Source file path |

**Response**: `201` — `ReportResponse`

### `GET /api/reports`

List reports with filters.

**Query Parameters**:

| Param | Type | Description |
|-------|------|-------------|
| experiment_id | string | Filter by experiment |
| report_type | string | Filter by type ("timing"/"utilization"/"runtime") |

**Response**: `200` — Array of `ReportResponse`

### `GET /api/reports/{report_id}`

Get a single report.

**Response**: `200` — `ReportResponse` | `404`

---

## Comparisons

### `POST /api/compare`

Compare exactly two experiments.

**Request Body**:

```json
{
  "experiment_ids": ["uuid-a", "uuid-b"]
}
```

**Response**: `200`

```json
{
  "experiment_ids": ["uuid-a", "uuid-b"],
  "deltas": {
    "wns": { "a": 0.456, "b": -1.234, "delta": -1.69 },
    "tns": { "a": 0.0, "b": -5.67, "delta": -5.67 },
    "lut": { "a": 45000.0, "b": 45230.0, "delta": 230.0 },
    "ff": { "a": 38000.0, "b": 38500.0, "delta": 500.0 },
    "bram": { "a": 200.0, "b": 200.0, "delta": 0.0 },
    "dsp": { "a": 50.0, "b": 50.0, "delta": 0.0 },
    "total_runtime": { "a": 1800.0, "b": 2100.0, "delta": 300.0 }
  },
  "option_diffs": {
    "seed": { "a": 1, "b": 42 },
    "strategy": { "a": "default", "b": "Performance_Explore" }
  }
}
```

**Error**: `404` if experiment IDs not found or not exactly 2 IDs provided.

---

## Predictions

### `POST /api/predict`

Predict build outcomes from an existing experiment or raw features.

**Request Body** (two modes):

Mode 1 — By experiment ID:

```json
{
  "experiment_id": "uuid"
}
```

Mode 2 — By raw features:

```json
{
  "device": "xcvu9p-flgb2104-2-e",
  "lut_pct": 45.0,
  "ff_pct": 38.0,
  "bram_pct": 20.0,
  "dsp_pct": 12.0,
  "seed": 42,
  "retiming": true,
  "phys_opt": false,
  "strategy": "Performance_Explore"
}
```

**Response**: `200`

```json
{
  "expected_wns": 0.345,
  "expected_compile_duration": 2400.0,
  "timing_success_probability": 0.78,
  "model_versions": {
    "timing": "v1",
    "runtime": "v1",
    "classifier": "v1"
  },
  "error": null
}
```

**Error**: `200` with `error` field if prediction engine unavailable or experiment not found.

### `POST /api/predict/train`

Trigger model retraining with synthetic data.

**Response**: `202`

```json
{
  "status": "trained",
  "results": {
    "timing_model": { "mae": 0.12, "rmse": 0.18 },
    "runtime_model": { "mae": 320.0, "rmse": 450.0 },
    "timing_classifier_model": { "accuracy": 0.89, "f1": 0.87 }
  }
}
```

### `GET /api/predict/models`

List trained model metadata from the database.

**Response**: `200` — Array of:

```json
{
  "id": "uuid",
  "model_type": "timing_model",
  "version": 1,
  "file_path": "packages/predictor/models/timing_model.pkl",
  "dataset_size": 2000,
  "accuracy": 0.89,
  "trained_at": "2026-01-01T00:00:00Z"
}
```

---

## Recommendations

### `POST /api/recommend`

Generate and persist recommendations for an experiment.

**Request Body**:

```json
{
  "experiment_id": "uuid"
}
```

**Response**: `200` — Array of `RecommendationResponse`:

```json
[
  {
    "id": "uuid",
    "experiment_id": "uuid",
    "rule_name": "R01_WNS_VIOLATION",
    "category": "timing",
    "priority": "critical",
    "message": "Timing violation detected (WNS=-1.234ns). Consider enabling retiming or increasing placement effort.",
    "confidence": 0.95,
    "created_at": "2026-01-01T00:00:00Z"
  }
]
```

**Rules** (R01–R12):

| Rule | Category | Trigger |
|------|----------|---------|
| R01 | timing | WNS < 0 |
| R02 | timing | TNS < -10 |
| R03 | timing | Failing paths > 100 |
| R04 | utilization | LUT utilization > 80% |
| R05 | utilization | BRAM utilization > 90% |
| R06 | utilization | DSP utilization > 95% |
| R07 | runtime | Synthesis > 1 hour |
| R08 | runtime | Implementation > 2 hours |
| R09 | runtime | Bitstream > 30 minutes |
| R10 | strategy | WNS < 0 and retiming not enabled |
| R11 | strategy | WNS < -0.5 and phys_opt not enabled |
| R12 | strategy | No seed sweep attempted |

---

## Error Responses

All errors follow the `FCIPError` format:

```json
{
  "error": "NotFoundError",
  "detail": "experiment abc-123 not found",
  "code": "FCIP_404"
}
```

| Error Type | HTTP Status |
|-----------|-------------|
| `ParseError` | 422 |
| `ImportError` | 400 |
| `NotFoundError` | 404 |
| `PredictionError` | 500 |
| `RecommendationError` | 500 |
