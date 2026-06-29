from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fcip_shared.exceptions import NotFoundError
from fcip_shared.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from fcip_shared.models.project import Project
from fcip_shared.models.experiment import Experiment
from fcip_backend.api.deps import get_db

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(name=body.name, path=body.path, description=body.description)
    db.add(project)
    await db.flush()
    count_q = await db.execute(
        select(func.count()).where(Experiment.project_id == project.id)
    )
    resp = ProjectResponse.model_validate(project)
    resp.experiment_count = count_q.scalar() or 0
    return resp


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).offset(offset).limit(limit).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    resp = []
    for p in projects:
        count_q = await db.execute(
            select(func.count()).where(Experiment.project_id == p.id)
        )
        r = ProjectResponse.model_validate(p)
        r.experiment_count = count_q.scalar() or 0
        resp.append(r)
    return resp


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == uuid.UUID(project_id)))
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError(f"project {project_id} not found")
    count_q = await db.execute(
        select(func.count()).where(Experiment.project_id == project.id)
    )
    resp = ProjectResponse.model_validate(project)
    resp.experiment_count = count_q.scalar() or 0
    return resp


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == uuid.UUID(project_id)))
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError(f"project {project_id} not found")
    await db.delete(project)
    await db.flush()
