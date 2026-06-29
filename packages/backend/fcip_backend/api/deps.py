from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from fcip_backend.database import get_db


__all__ = ["get_db"]
