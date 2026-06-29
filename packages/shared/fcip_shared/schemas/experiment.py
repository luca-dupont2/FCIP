from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ExperimentCreate(BaseModel):
    project_id: uuid.UUID
    name: str | None = None
    git_commit: str | None = Field(None, max_length=40)
    branch: str | None = Field(None, max_length=255)
    repository_name: str | None = Field(None, max_length=255)
    tool: str = Field(..., max_length=50)
    tool_version: str | None = Field(None, max_length=50)
    device: str | None = Field(None, max_length=100)
    seed: int | None = None
    status: str = "running"
    compile_options: dict | None = {}
    machine_info: dict | None = {}
    changed_files: list[str] | None = []
    completed_at: datetime | None = None
    source: str = "tracked"


class ExperimentUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    completed_at: datetime | None = None


class ExperimentResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str | None = None
    git_commit: str | None = None
    branch: str | None = None
    repository_name: str | None = None
    tool: str
    tool_version: str | None = None
    device: str | None = None
    seed: int | None = None
    status: str
    compile_options: dict | None = {}
    machine_info: dict | None = {}
    changed_files: list | None = []
    created_at: datetime
    completed_at: datetime | None = None
    source: str = "tracked"

    model_config = {"from_attributes": True}


class ExperimentListResponse(BaseModel):
    items: list[ExperimentResponse]
    total: int
    limit: int
    offset: int
