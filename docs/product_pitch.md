# FCIP — FPGA Compile Intelligence Platform

## The Problem

Every FPGA engineer knows this pain: you kick off a Vivado build, wait 2-8 hours, and it fails timing. You change a constraint, run it again, wait another 3 hours. After a week of iteration, you finally close timing — but you have no idea which change actually fixed it, and you can't reproduce it if the design regresses.

Current workflows are broken:
- **No memory** — Each build is an isolated event. No one tracks what changed between runs, what options were tried, or what the results were.
- **No prediction** — Before hitting "Run", you have zero indication whether the build will close timing or take 4 hours to fail.
- **No guidance** — When timing fails, you're on your own. No tool tells you "enable retiming" or "reduce BRAM utilization below 75%."
- **No learning** — After 500 builds across a project, you've accumulated zero institutional knowledge. Every new engineer starts from scratch.

## The Product

FCIP is a **local-first compile observability platform** for FPGA teams. It watches your builds, remembers everything, predicts outcomes, and tells you what to do next.

### Three core capabilities:

**1. Track — Build Memory**

Plug FCIP into your existing workflow. One command:

```
fcip init --name my_design --tool vivado
fcip track ./build_output/
```

Every build is automatically captured: timing results, utilization, compile options, git commit, seed, device, runtime. No manual logging. No spreadsheets. Every experiment is queryable and comparable.

Compare any two builds side-by-side:
```
fcip compare <run_a> <run_b>
```
See exactly what changed: WNS delta, utilization shifts, option differences. The days of "which build was better?" are over.

**2. Predict — Build Intelligence**

After your team accumulates build history, FCIP learns from it:

```
fcip predict --device xcvu9p --lut-pct 45 --seed 42
```

Get three answers before you press "Run":
- **Expected WNS**: Will this build close timing?
- **Expected compile duration**: How long will this take? (Know before committing to a 4-hour build.)
- **Timing success probability**: Percentage chance of meeting timing.

The models improve with every build you track. More usage = better predictions. Your data, your models, on your machine.

**3. Recommend — Build Guidance**

When timing fails, FCIP tells you what to try:

```
fcip recommend <experiment_id>
```

12 deterministic rules analyze your build and prioritize actionable fixes:
- "LUT utilization at 89% — consider logic replication or pipelining"
- "Retiming not enabled — may improve timing on this path"
- "WNS = -1.2ns with 12 failing paths — suggest physical optimization"
- "Previous builds in this project closed timing with seed 3"

Recommendations are sorted by priority (high → low) with confidence scores. No guessing.

### Dashboard

A full web dashboard (React + Mantine) gives your team a shared view:

- **Experiments** — Browse, search, filter all builds by status, tool, device, branch
- **Comparisons** — Side-by-side metric deltas with visual indicators
- **Predictions** — Interactive prediction form with visual result cards
- **Recommendations** — Prioritized action list per experiment
- **Projects** — Organized by design, per-project experiment history

All data is also available via REST API at `localhost:8000/docs` (Swagger UI).

## How It Works

```
Your Vivado/Quartus Build
        │
        ▼
   fcip track          ← Parses .rpt/.log files automatically
        │
        ▼
   PostgreSQL DB       ← All experiments, reports, recommendations
        │
        ├────────────── fcip predict     ← ML models (Random Forest)
        ├────────────── fcip recommend   ← 12 deterministic rules
        └────────────── Dashboard        ← React web UI
```

**Stack**: Python 3.12 + FastAPI backend, PostgreSQL 16, scikit-learn ML, React 19 dashboard, Typer CLI.

**Parsers**: Native support for Vivado (timing, utilization, runtime) and Quartus (timing, utilization, runtime) report formats. No manual data entry.

**Local-first**: Everything runs on your machine. No cloud. No API keys. No data leaves your network. Your proprietary design data stays proprietary.

## Why This Matters

The FPGA industry has no tool like this. EDA vendors give you the compiler. They don't give you a memory layer, a prediction engine, or a recommendation system for your builds.

**Plunify InTime** is the commercial alternative — closed-source, expensive licensing, cloud or cluster deployment. Their moat: 20M+ build results across thousands of customers. But your data leaves your machine, and you can't see or modify how their ML works.

**Academics** publish DSE papers with private datasets that are never shared. No public models exist for FPGA build prediction. Not on HuggingFace. Not from AMD/Xilinx. Not from Intel.

FCIP is the **open, local-first alternative**:
- **Privacy**: Your data never leaves your machine (unlike InTime Cloud)
- **Transparency**: See every line of code, understand exactly how models are trained
- **Control**: Modify parsers, change models, customize for your workflow
- **Cost**: Free (vs. commercial licensing)
- **Learning**: Understand the ML, not just use it as a black box

**Tradeoff**: InTime has 20M builds and auto-pilot optimization. FCIP starts with synthetic data and requires manual tracking. But after 50+ of **your** builds, FCIP knows **your** designs better than any generic model ever could.

## Current State (MVP)

| Capability | Status |
|-----------|--------|
| Build tracking (init, track, compare) | Done |
| CLI (5 commands) | Done |
| REST API (6 routers, 16 endpoints) | Done |
| Web dashboard (7 pages) | Done |
| Prediction (3 RF models, synthetic data) | Done — pipeline works, predictions improve with real data |
| Recommendations (12 rules, 4 categories) | Done |
| Docker deployment | Done |
| Test suite (68 Python, 16 frontend) | Done |

**The honest caveat**: Models are trained on synthetic data today. Predictions are directionally useful but not production-accurate. This is by design — the pipeline is complete and validated. The data flywheel starts when your team tracks real builds.

## The Roadmap

**Now (MVP)**: Track, compare, predict (synthetic), recommend. Pipeline works end-to-end.

**V1 (User builds)**: Your team's own build history trains project-specific models. Every `fcip track` makes predictions better for *your* designs. Optional dataset export/import for team-level data pooling. This is where FCIP becomes irreplaceable — the more you use it, the more valuable it becomes, and no competitor can replicate your private training data.

**Not pursuing**: HLSFactory benchmark integration. HLS synthesis estimates ≠ post-implementation timing, and generic benchmarks don't capture your proprietary designs. Strategic focus: user's own tracked builds.

## Get Started

```bash
cp .env.example .env
uv sync --all-packages
uvicorn fcip_backend.main:app --reload --port 8000   # backend
cd frontend && npm run dev                            # dashboard
```

Or: `docker compose up` — everything running in 60 seconds.

---

**FCIP: Stop forgetting your builds. Start learning from them.**
