from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ReportCreate(BaseModel):
    experiment_id: uuid.UUID
    report_type: str
    wns: float | None = None
    tns: float | None = None
    failing_paths: int | None = None
    critical_path: str | None = None
    lut: int | None = None
    lut_available: int | None = None
    ff: int | None = None
    ff_available: int | None = None
    bram: int | None = None
    bram_available: int | None = None
    dsp: int | None = None
    dsp_available: int | None = None
    io_used: int | None = None
    io_available: int | None = None
    clock_utilization: float | None = None
    synthesis_duration: float | None = None
    implementation_duration: float | None = None
    bitstream_duration: float | None = None
    total_runtime: float | None = None
    raw_content: str | None = None
    source_file: str | None = None


class ReportResponse(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID
    report_type: str
    wns: float | None = None
    tns: float | None = None
    failing_paths: int | None = None
    critical_path: str | None = None
    lut: int | None = None
    lut_available: int | None = None
    ff: int | None = None
    ff_available: int | None = None
    bram: int | None = None
    bram_available: int | None = None
    dsp: int | None = None
    dsp_available: int | None = None
    io_used: int | None = None
    io_available: int | None = None
    clock_utilization: float | None = None
    synthesis_duration: float | None = None
    implementation_duration: float | None = None
    bitstream_duration: float | None = None
    total_runtime: float | None = None
    raw_content: str | None = None
    source_file: str | None = None
    parsed_at: datetime

    model_config = {"from_attributes": True}
