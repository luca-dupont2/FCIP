from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://fcip:fcip@localhost:5432/fcip"

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "console"

    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    CACHE_TTL: int = 60
    MODEL_DIR: str = "./models"
    ARTIFACT_STORAGE: str = "./artifacts"

    SYNTHETIC_SAMPLES: int = 2000
    MODEL_RETRAIN_THRESHOLD: int = 100
    MIN_REAL_SAMPLES: int = 50
    REAL_SAMPLE_WEIGHT: float = 5.0
    SYNTHETIC_SAMPLE_WEIGHT: float = 1.0


def get_settings() -> AppSettings:
    return AppSettings()
