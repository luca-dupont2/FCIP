from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fcip_shared.schemas.recommendation import RecommendRequest, RecommendationResponse
from fcip_shared.models.experiment import Experiment
from fcip_shared.models.report import Report
from fcip_shared.models.recommendation import Recommendation
from fcip_backend.api.deps import get_db

router = APIRouter()


@router.post("", response_model=list[RecommendationResponse])
async def recommend(body: RecommendRequest, db: AsyncSession = Depends(get_db)):
    exp_result = await db.execute(
        select(Experiment).where(Experiment.id == body.experiment_id)
    )
    exp = exp_result.scalar_one_or_none()

    proj_experiments = []
    if exp:
        proj_result = await db.execute(
            select(Experiment).where(Experiment.project_id == exp.project_id)
        )
        proj_experiments = proj_result.scalars().all()

    rpt_result = await db.execute(
        select(Report).where(Report.experiment_id == body.experiment_id)
    )
    reports = rpt_result.scalars().all()

    from fcip_recommender.engine import RecommendationEngine
    engine = RecommendationEngine()
    recs = engine.evaluate(exp, reports, proj_experiments)

    saved = []
    for rec in recs:
        db_rec = Recommendation(
            experiment_id=body.experiment_id,
            rule_name=rec.rule_name,
            category=rec.category,
            priority=rec.priority.value if rec.priority else None,
            message=rec.message,
            confidence=rec.confidence,
        )
        db.add(db_rec)
        saved.append(db_rec)

    await db.flush()

    return [RecommendationResponse.model_validate(r) for r in saved]
