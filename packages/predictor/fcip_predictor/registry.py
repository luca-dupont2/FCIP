from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fcip_shared.models.model_metadata import ModelMetadata


class ModelRegistry:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(
        self,
        model_type: str,
        version: int,
        file_path: str,
        dataset_size: int | None = None,
        accuracy: float | None = None,
        training_duration: float | None = None,
        hyperparams: dict | None = None,
        data_source: str = "synthetic",
    ) -> ModelMetadata:
        meta = ModelMetadata(
            id=uuid.uuid4(),
            model_type=model_type,
            version=version,
            file_path=file_path,
            dataset_size=dataset_size,
            accuracy=accuracy,
            training_duration=training_duration,
            trained_at=datetime.now(timezone.utc),
            hyperparams=hyperparams or {},
            data_source=data_source,
            is_active=True,
        )
        self.db.add(meta)
        await self.db.flush()
        return meta

    async def deactivate_previous(self, model_type: str) -> int:
        result = await self.db.execute(
            update(ModelMetadata)
            .where(ModelMetadata.model_type == model_type)
            .where(ModelMetadata.is_active == True)
            .values(is_active=False)
        )
        await self.db.flush()
        return result.rowcount

    async def get_active(self, model_type: str) -> ModelMetadata | None:
        result = await self.db.execute(
            select(ModelMetadata)
            .where(ModelMetadata.model_type == model_type)
            .where(ModelMetadata.is_active == True)
            .order_by(ModelMetadata.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest(self, model_type: str) -> ModelMetadata | None:
        result = await self.db.execute(
            select(ModelMetadata)
            .where(ModelMetadata.model_type == model_type)
            .order_by(ModelMetadata.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ModelMetadata]:
        result = await self.db.execute(
            select(ModelMetadata).order_by(ModelMetadata.trained_at.desc())
        )
        return list(result.scalars().all())
