from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    path: str | None = None
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    path: str | None = None
    description: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    path: str | None = None
    description: str | None = None
    experiment_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
