from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fcip_shared.exceptions import NotFoundError
from fcip_shared.schemas.comparison import CompareRequest, CompareResponse, MetricDelta
from fcip_shared.models.experiment import Experiment
from fcip_shared.models.report import Report
from fcip_backend.api.deps import get_db

router = APIRouter()


@router.post("", response_model=CompareResponse)
async def compare_experiments(body: CompareRequest, db: AsyncSession = Depends(get_db)):
    if len(body.experiment_ids) != 2:
        raise NotFoundError("comparison requires exactly 2 experiment IDs")

    exp_ids = [uuid.UUID(eid) for eid in body.experiment_ids]

    results = {}
    reports_map = {}
    for eid in exp_ids:
        exp_result = await db.execute(select(Experiment).where(Experiment.id == eid))
        exp = exp_result.scalar_one_or_none()
        if not exp:
            raise NotFoundError(f"experiment {eid} not found")

        report_result = await db.execute(
            select(Report).where(Report.experiment_id == eid)
        )
        reports = report_result.scalars().all()
        results[str(eid)] = exp
        reports_map[str(eid)] = reports[0] if reports else None

    a_id, b_id = body.experiment_ids[0], body.experiment_ids[1]
    exp_a, exp_b = results[a_id], results[b_id]
    rpt_a, rpt_b = reports_map[a_id], reports_map[b_id]

    deltas: dict[str, MetricDelta] = {}

    metrics = [
        ("wns", lambda r: r.wns if r else None),
        ("tns", lambda r: r.tns if r else None),
        ("lut", lambda r: float(r.lut) if r and r.lut else None),
        ("ff", lambda r: float(r.ff) if r and r.ff else None),
        ("bram", lambda r: float(r.bram) if r and r.bram else None),
        ("dsp", lambda r: float(r.dsp) if r and r.dsp else None),
        ("total_runtime", lambda r: r.total_runtime if r else None),
    ]

    for name, getter in metrics:
        val_a = getter(rpt_a)
        val_b = getter(rpt_b)
        delta = None
        if val_a is not None and val_b is not None:
            delta = val_b - val_a
        deltas[name] = MetricDelta(a=val_a, b=val_b, delta=delta)

    option_diffs: dict[str, dict] = {}
    opts_a = exp_a.compile_options or {}
    opts_b = exp_b.compile_options or {}
    all_keys = set(list(opts_a.keys()) + list(opts_b.keys()))
    for key in all_keys:
        if opts_a.get(key) != opts_b.get(key):
            option_diffs[key] = {"a": opts_a.get(key), "b": opts_b.get(key)}
    if exp_a.seed != exp_b.seed:
        option_diffs["seed"] = {"a": exp_a.seed, "b": exp_b.seed}

    return CompareResponse(
        experiment_ids=body.experiment_ids,
        deltas=deltas,
        option_diffs=option_diffs,
    )
