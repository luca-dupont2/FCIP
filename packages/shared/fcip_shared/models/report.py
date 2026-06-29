from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fcip_shared.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)

    wns: Mapped[float | None] = mapped_column(Float, nullable=True)
    tns: Mapped[float | None] = mapped_column(Float, nullable=True)
    failing_paths: Mapped[int | None] = mapped_column(Integer, nullable=True)
    critical_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    lut: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lut_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ff: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ff_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bram: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bram_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dsp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dsp_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    io_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    io_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clock_utilization: Mapped[float | None] = mapped_column(Float, nullable=True)

    synthesis_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    implementation_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    bitstream_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_runtime: Mapped[float | None] = mapped_column(Float, nullable=True)

    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    experiment: Mapped["Experiment"] = relationship(back_populates="reports")

    __table_args__ = (
        Index("idx_reports_experiment", "experiment_id"),
        Index("idx_reports_type", "report_type"),
    )
