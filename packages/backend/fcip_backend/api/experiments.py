from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from fcip_shared.exceptions import NotFoundError
from fcip_shared.schemas.experiment import ExperimentCreate, ExperimentUpdate, ExperimentResponse, ExperimentListResponse
from fcip_shared.schemas.report import ReportResponse
from fcip_shared.models.experiment import Experiment
from fcip_shared.models.report import Report
from fcip_backend.api.deps import get_db

router = APIRouter()


@router.post("", response_model=ExperimentResponse, status_code=201)
async def create_experiment(body: ExperimentCreate, db: AsyncSession = Depends(get_db)):
    exp = Experiment(
        project_id=body.project_id,
        name=body.name,
        git_commit=body.git_commit,
        branch=body.branch,
        repository_name=body.repository_name,
        tool=body.tool,
        tool_version=body.tool_version,
        device=body.device,
        seed=body.seed,
        status=body.status,
        compile_options=body.compile_options or {},
        machine_info=body.machine_info or {},
        changed_files=body.changed_files or [],
        completed_at=body.completed_at,
        source=body.source,
    )
    db.add(exp)
    await db.flush()
    return ExperimentResponse.model_validate(exp)


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(
    project_id: str | None = None,
    tool: str | None = None,
    status: str | None = None,
    branch: str | None = None,
    seed: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Experiment)
    count_query = select(func.count()).select_from(Experiment)

    if project_id:
        query = query.where(Experiment.project_id == uuid.UUID(project_id))
        count_query = count_query.where(Experiment.project_id == uuid.UUID(project_id))
    if tool:
        query = query.where(Experiment.tool == tool)
        count_query = count_query.where(Experiment.tool == tool)
    if status:
        query = query.where(Experiment.status == status)
        count_query = count_query.where(Experiment.status == status)
    if branch:
        query = query.where(Experiment.branch == branch)
        count_query = count_query.where(Experiment.branch == branch)
    if seed is not None:
        query = query.where(Experiment.seed == seed)
        count_query = count_query.where(Experiment.seed == seed)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(Experiment.created_at.desc()).offset(offset).limit(limit)
    )
    experiments = result.scalars().all()

    return ExperimentListResponse(
        items=[ExperimentResponse.model_validate(e) for e in experiments],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=ExperimentListResponse)
async def search_experiments(
    q: str = "",
    project_id: str | None = None,
    tool: str | None = None,
    min_wns: float | None = None,
    max_wns: float | None = None,
    seed: int | None = None,
    branch: str | None = None,
    sort_by: str = "created_at:desc",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Experiment)
    count_query = select(func.count()).select_from(Experiment)

    if project_id:
        query = query.where(Experiment.project_id == uuid.UUID(project_id))
        count_query = count_query.where(Experiment.project_id == uuid.UUID(project_id))
    if tool:
        query = query.where(Experiment.tool == tool)
        count_query = count_query.where(Experiment.tool == tool)
    if branch:
        query = query.where(Experiment.branch == branch)
        count_query = count_query.where(Experiment.branch == branch)
    if seed is not None:
        query = query.where(Experiment.seed == seed)
        count_query = count_query.where(Experiment.seed == seed)

    if q:
        ql = q.lower().strip()
        if "best" in ql and "wns" in ql:
            sort_by = "wns:asc"
        elif "worst" in ql and "wns" in ql:
            sort_by = "wns:desc"

    if "wns:asc" in sort_by:
        query = query.join(Report, Report.experiment_id == Experiment.id, isouter=True).order_by(Report.wns.asc().nulls_last())
    elif "wns:desc" in sort_by:
        query = query.join(Report, Report.experiment_id == Experiment.id, isouter=True).order_by(Report.wns.desc().nulls_last())
    elif "created_at:asc" in sort_by:
        query = query.order_by(Experiment.created_at.asc())
    else:
        query = query.order_by(Experiment.created_at.desc())

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query.offset(offset).limit(limit))
    experiments = result.scalars().all()

    return ExperimentListResponse(
        items=[ExperimentResponse.model_validate(e) for e in experiments],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Experiment).where(Experiment.id == uuid.UUID(experiment_id))
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise NotFoundError(f"experiment {experiment_id} not found")
    return ExperimentResponse.model_validate(exp)


@router.patch("/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(
    experiment_id: str,
    body: ExperimentUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Experiment).where(Experiment.id == uuid.UUID(experiment_id))
    )
    exp = result.scalar_one_or_none()
    if not exp:
        raise NotFoundError(f"experiment {experiment_id} not found")
    if body.name is not None:
        exp.name = body.name
    if body.status is not None:
        exp.status = body.status
    if body.completed_at is not None:
        exp.completed_at = body.completed_at
    await db.flush()
    return ExperimentResponse.model_validate(exp)
