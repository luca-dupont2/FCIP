from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class RecommendRequest(BaseModel):
    experiment_id: uuid.UUID


class RecommendationResponse(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID
    rule_name: str
    category: str
    priority: str | None = None
    message: str
    confidence: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
