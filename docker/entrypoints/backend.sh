#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "Ensuring database tables exist..."
python -c "from fcip_shared.database import init_db; import asyncio; asyncio.run(init_db())"

echo "Running database migrations..."
alembic upgrade head || echo "Migration note: will retry on next start"

echo "Starting FCIP backend..."
exec uvicorn fcip_backend.main:app --host 0.0.0.0 --port 8000
