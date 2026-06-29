from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ArtifactCreate(BaseModel):
    experiment_id: uuid.UUID
    path: str
    artifact_type: str = Field(..., max_length=50)
    size_bytes: int | None = None
    checksum: str | None = Field(None, max_length=64)
    modification_time: datetime | None = None


class ArtifactResponse(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID
    path: str
    artifact_type: str
    size_bytes: int | None = None
    checksum: str | None = None
    modification_time: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
