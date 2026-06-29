from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fcip_shared.exceptions import NotFoundError
from fcip_shared.schemas.report import ReportCreate, ReportResponse
from fcip_shared.models.report import Report
from fcip_backend.api.deps import get_db

router = APIRouter()


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(body: ReportCreate, db: AsyncSession = Depends(get_db)):
    report = Report(
        experiment_id=body.experiment_id,
        report_type=body.report_type,
        wns=body.wns,
        tns=body.tns,
        failing_paths=body.failing_paths,
        critical_path=body.critical_path,
        lut=body.lut,
        lut_available=body.lut_available,
        ff=body.ff,
        ff_available=body.ff_available,
        bram=body.bram,
        bram_available=body.bram_available,
        dsp=body.dsp,
        dsp_available=body.dsp_available,
        io_used=body.io_used,
        io_available=body.io_available,
        clock_utilization=body.clock_utilization,
        synthesis_duration=body.synthesis_duration,
        implementation_duration=body.implementation_duration,
        bitstream_duration=body.bitstream_duration,
        total_runtime=body.total_runtime,
        raw_content=body.raw_content,
        source_file=body.source_file,
    )
    db.add(report)
    await db.flush()
    return ReportResponse.model_validate(report)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == uuid.UUID(report_id)))
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundError(f"report {report_id} not found")
    return ReportResponse.model_validate(report)


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    experiment_id: str | None = None,
    report_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Report)
    if experiment_id:
        query = query.where(Report.experiment_id == uuid.UUID(experiment_id))
    if report_type:
        query = query.where(Report.report_type == report_type)
    result = await db.execute(query.order_by(Report.parsed_at.desc()))
    reports = result.scalars().all()
    return [ReportResponse.model_validate(r) for r in reports]
