from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from fcip_shared.database import Base
import fcip_shared.models  # noqa: F401
from fcip_shared.models.model_metadata import ModelMetadata
from fcip_predictor.registry import ModelRegistry

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def registry_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def registry_session(registry_engine):
    factory = async_sessionmaker(registry_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.mark.asyncio
class TestModelRegistry:
    async def test_register_model(self, registry_session):
        registry = ModelRegistry(registry_session)
        meta = await registry.register(
            model_type="timing_model",
            version=1,
            file_path="/tmp/timing_model.pkl",
            dataset_size=100,
            accuracy=0.85,
            training_duration=5.0,
            data_source="synthetic",
        )
        await registry_session.flush()
        assert meta.model_type == "timing_model"
        assert meta.version == 1
        assert meta.is_active is True
        assert meta.data_source == "synthetic"

    async def test_deactivate_previous(self, registry_session):
        registry = ModelRegistry(registry_session)
        await registry.register(
            model_type="timing_model", version=1, file_path="/tmp/v1.pkl", data_source="synthetic",
        )
        await registry_session.flush()

        count = await registry.deactivate_previous("timing_model")
        await registry_session.flush()
        assert count == 1

        meta = await registry.get_active("timing_model")
        assert meta is None

    async def test_deactivate_previous_only_affects_same_type(self, registry_session):
        registry = ModelRegistry(registry_session)
        await registry.register(
            model_type="timing_model", version=1, file_path="/tmp/v1.pkl", data_source="synthetic",
        )
        await registry.register(
            model_type="runtime_model", version=1, file_path="/tmp/rt_v1.pkl", data_source="synthetic",
        )
        await registry_session.flush()

        count = await registry.deactivate_previous("timing_model")
        await registry_session.flush()
        assert count == 1

        rt_meta = await registry.get_active("runtime_model")
        assert rt_meta is not None
        assert rt_meta.is_active is True

        tm_meta = await registry.get_active("timing_model")
        assert tm_meta is None

    async def test_get_active(self, registry_session):
        registry = ModelRegistry(registry_session)
        await registry.register(
            model_type="timing_model", version=1, file_path="/tmp/v1.pkl", data_source="synthetic",
        )
        await registry_session.flush()

        meta = await registry.get_active("timing_model")
        assert meta is not None
        assert meta.version == 1
        assert meta.is_active is True

    async def test_get_active_none(self, registry_session):
        registry = ModelRegistry(registry_session)
        meta = await registry.get_active("nonexistent_model")
        assert meta is None

    async def test_register_and_deactivate_flow(self, registry_session):
        registry = ModelRegistry(registry_session)

        await registry.register(
            model_type="timing_model", version=1, file_path="/tmp/v1.pkl", data_source="synthetic",
        )
        await registry_session.flush()

        await registry.deactivate_previous("timing_model")
        await registry.register(
            model_type="timing_model", version=2, file_path="/tmp/v2.pkl", data_source="real",
        )
        await registry_session.flush()

        active = await registry.get_active("timing_model")
        assert active is not None
        assert active.version == 2
        assert active.data_source == "real"

        latest = await registry.get_latest("timing_model")
        assert latest is not None
        assert latest.version == 2

    async def test_list_all(self, registry_session):
        registry = ModelRegistry(registry_session)
        await registry.register(
            model_type="timing_model", version=1, file_path="/tmp/v1.pkl", data_source="synthetic",
        )
        await registry.register(
            model_type="runtime_model", version=1, file_path="/tmp/rt_v1.pkl", data_source="synthetic",
        )
        await registry_session.flush()

        all_models = await registry.list_all()
        assert len(all_models) == 2
