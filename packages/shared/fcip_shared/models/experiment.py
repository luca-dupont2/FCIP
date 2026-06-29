from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Index, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fcip_shared.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    git_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repository_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tool: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    device: Mapped[str | None] = mapped_column(String(100), nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    compile_options: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    machine_info: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    changed_files: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="tracked")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="experiments")
    reports: Mapped[list["Report"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan", lazy="selectin"
    )
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan", lazy="selectin"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_experiments_project", "project_id"),
        Index("idx_experiments_tool", "tool"),
        Index("idx_experiments_status", "status"),
        Index("idx_experiments_branch", "branch"),
        Index("idx_experiments_device", "device"),
        Index("idx_experiments_seed", "seed"),
        Index("idx_experiments_git_commit", "git_commit"),
    )
