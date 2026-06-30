# Database Schema

PostgreSQL 16 with SQLAlchemy 2.0 async ORM. All tables use UUID primary keys and timezone-aware timestamps.

## Entity-Relationship Diagram

```
projects ──1:N──▶ experiments ──1:N──▶ reports
                     │
                     ├──1:N──▶ artifacts
                     │
                     └──1:N──▶ recommendations

model_metadata  (standalone)
```

---

## Tables

### `projects`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default `uuid_generate_v4()` | Primary key |
| name | VARCHAR(255) | UNIQUE, NOT NULL | Project name |
| path | TEXT | nullable | Filesystem path to project |
| description | TEXT | nullable | Human description |
| created_at | TIMESTAMPTZ | NOT NULL, default `now()` | Creation time |
| updated_at | TIMESTAMPTZ | NOT NULL, default `now()`, on update | Last modification time |

---

### `experiments`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Primary key |
| project_id | UUID | FK → projects.id, CASCADE | Parent project |
| name | VARCHAR(255) | nullable | Human-readable name |
| git_commit | VARCHAR(40) | nullable | Commit SHA |
| branch | VARCHAR(255) | nullable | Git branch |
| repository_name | VARCHAR(255) | nullable | Repository name |
| tool | VARCHAR(50) | NOT NULL | "vivado" or "quartus" |
| tool_version | VARCHAR(50) | nullable | e.g. "2024.1" |
| device | VARCHAR(100) | nullable | Target FPGA part number |
| seed | INTEGER | nullable | Implementation seed |
| status | VARCHAR(20) | NOT NULL, default "running" | running/success/failed/timeout |
| compile_options | JSON | nullable, default `{}` | Strategy, retiming, phys_opt, etc. |
| machine_info | JSON | nullable, default `{}` | CPU, RAM, OS info |
| changed_files | JSON | nullable, default `[]` | List of changed filenames |
| source | VARCHAR(20) | NOT NULL, default "tracked" | "tracked", "synthetic", "user_upload" |
| created_at | TIMESTAMPTZ | NOT NULL | Creation time |
| completed_at | TIMESTAMPTZ | nullable | Completion time |

**Indexes**:
- `idx_experiments_project` on `project_id`
- `idx_experiments_tool` on `tool`
- `idx_experiments_status` on `status`
- `idx_experiments_branch` on `branch`
- `idx_experiments_device` on `device`
- `idx_experiments_seed` on `seed`
- `idx_experiments_git_commit` on `git_commit`

---

### `reports`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Primary key |
| experiment_id | UUID | FK → experiments.id, CASCADE | Parent experiment |
| report_type | VARCHAR(20) | NOT NULL | "timing", "utilization", "runtime", "hls_synth", "combined" |
| wns | FLOAT | nullable | Worst Negative Slack (ns) |
| tns | FLOAT | nullable | Total Negative Slack (ns) |
| failing_paths | INTEGER | nullable | Number of failing paths |
| critical_path | TEXT | nullable | Critical path description |
| lut | INTEGER | nullable | LUTs used |
| lut_available | INTEGER | nullable | LUTs available |
| ff | INTEGER | nullable | Flip-flops used |
| ff_available | INTEGER | nullable | Flip-flops available |
| bram | INTEGER | nullable | Block RAMs used |
| bram_available | INTEGER | nullable | Block RAMs available |
| dsp | INTEGER | nullable | DSP blocks used |
| dsp_available | INTEGER | nullable | DSP blocks available |
| io_used | INTEGER | nullable | IO pins used |
| io_available | INTEGER | nullable | IO pins available |
| clock_utilization | FLOAT | nullable | Clock utilization % |
| synthesis_duration | FLOAT | nullable | Synthesis runtime (seconds) |
| implementation_duration | FLOAT | nullable | Implementation runtime (seconds) |
| bitstream_duration | FLOAT | nullable | Bitstream generation time (seconds) |
| total_runtime | FLOAT | nullable | Total build time (seconds) |
| raw_content | TEXT | nullable | Original report file content |
| source_file | TEXT | nullable | Source file path |
| parsed_at | TIMESTAMPTZ | NOT NULL | When report was parsed |

**Indexes**:
- `idx_reports_experiment` on `experiment_id`
- `idx_reports_type` on `report_type`

---

### `artifacts`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Primary key |
| experiment_id | UUID | FK → experiments.id, CASCADE | Parent experiment |
| path | TEXT | NOT NULL | File path (no copy, reference only) |
| artifact_type | VARCHAR(50) | NOT NULL | e.g. "bitstream", "checkpoint" |
| size_bytes | BIGINT | nullable | File size |
| checksum | VARCHAR(64) | nullable | SHA-256 checksum |
| modification_time | TIMESTAMPTZ | nullable | File mtime |
| created_at | TIMESTAMPTZ | NOT NULL | Record creation time |

**Indexes**:
- `idx_artifacts_experiment` on `experiment_id`

---

### `recommendations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Primary key |
| experiment_id | UUID | FK → experiments.id, CASCADE | Parent experiment |
| rule_name | VARCHAR(100) | NOT NULL | e.g. "R01_WNS_VIOLATION" |
| category | VARCHAR(50) | NOT NULL | "timing", "utilization", "runtime", "strategy" |
| priority | VARCHAR(20) | nullable | "critical", "high", "medium", "low" |
| message | TEXT | NOT NULL | Recommendation text |
| confidence | FLOAT | nullable | Rule confidence (0–1) |
| created_at | TIMESTAMPTZ | NOT NULL | When the recommendation was generated |

**Indexes**:
- `idx_recommendations_experiment` on `experiment_id`

---

### `model_metadata`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Primary key |
| model_type | VARCHAR(50) | NOT NULL | "timing_model", "runtime_model", "timing_classifier_model" |
| version | INTEGER | NOT NULL, default 1 | Model version number |
| file_path | TEXT | NOT NULL | Path to `.pkl` file |
| dataset_size | INTEGER | nullable | Training dataset rows |
| accuracy | FLOAT | nullable | Model accuracy/F1 score |
| training_duration | FLOAT | nullable | Training time (seconds) |
| trained_at | TIMESTAMPTZ | NOT NULL | Training timestamp |
| hyperparams | JSON | nullable, default `{}` | Model hyperparameters |
| data_source | VARCHAR(20) | NOT NULL, default "synthetic" | "synthetic", "real", "mixed" |
| is_active | BOOLEAN | NOT NULL, default true | Whether this model is currently active |
| project_id | UUID | FK → projects.id, SET NULL | Optional project-specific model |

No foreign keys except optional `project_id` — mostly standalone metadata table.

---

## Migration

Schema is managed via Alembic:

```bash
cd packages/backend
alembic upgrade head       # apply all migrations
alembic revision --autogenerate -m "description"  # create new migration
```

The async Alembic environment is configured in `packages/backend/alembic/env.py` to use `fcip_shared.database` for the engine and `Base.metadata` for autogeneration.

**Note on JSON vs JSONB**: All JSON columns use portable `JSON` type (not PostgreSQL-specific `JSONB`) to maintain SQLite compatibility for tests. Tests run on in-memory SQLite which doesn't support `JSONB`.
