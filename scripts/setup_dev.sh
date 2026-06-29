#!/usr/bin/env bash
set -euo pipefail

echo "=== FCIP Development Setup ==="

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "ERROR: Python 3.12+ required"; exit 1; }
python3 -c "import sys; assert sys.version_info >= (3, 12)" 2>/dev/null || { echo "ERROR: Python 3.12+ required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "WARNING: Node.js not found (needed for frontend)"; }
command -v psql >/dev/null 2>&1 || { echo "WARNING: PostgreSQL not found"; }

# Create .env from example if missing
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

# Install Python packages via uv
if command -v uv >/dev/null 2>&1; then
    echo "Installing Python packages via uv..."
    uv sync
else
    echo "ERROR: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install frontend
if [ -d frontend ] && [ -f frontend/package.json ]; then
    echo "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start development:"
echo "  Backend:   uvicorn fcip_backend.main:app --reload"
echo "  Frontend:  cd frontend && npm run dev"
echo "  CLI:       fcip --help"
echo ""
echo "  Or use Docker: docker compose up"
