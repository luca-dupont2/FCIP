"""Run database migrations and optionally seed with synthetic data."""
from __future__ import annotations

import asyncio

from fcip_shared.database import init_db, close_db


async def main() -> None:
    print("Running database migrations...")
    await init_db()
    print("Database schema created successfully.")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
