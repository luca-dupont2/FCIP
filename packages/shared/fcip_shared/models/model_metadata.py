from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, Text, DateTime, JSON, Boolean, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from fcip_shared.database import Base


class ModelMetadata(Base):
    __tablename__ = "model_metadata"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    hyperparams: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    data_source: Mapped[str] = mapped_column(String(20), nullable=False, default="synthetic")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
