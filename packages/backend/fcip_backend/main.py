from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fcip_shared.config import get_settings
from fcip_shared.logging_config import setup_logging
from fcip_shared.exceptions import FCIPError, ParseError, ImportError as ImportErr, PredictionError, RecommendationError, NotFoundError, InsufficientTrainingDataError

from fcip_backend.api.projects import router as projects_router
from fcip_backend.api.experiments import router as experiments_router
from fcip_backend.api.reports import router as reports_router
from fcip_backend.api.comparisons import router as comparisons_router
from fcip_backend.api.predictions import router as predictions_router
from fcip_backend.api.recommendations import router as recommendations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from fcip_shared.database import init_db, close_db
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

    app = FastAPI(
        title="FCIP - FPGA Compile Intelligence Platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        import structlog
        import time
        logger = structlog.get_logger("fcip.backend")
        start = time.time()
        response: Response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "request",
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        return response

    @app.exception_handler(FCIPError)
    async def fcip_error_handler(request: Request, exc: FCIPError):
        status_map = {
            ParseError: 422,
            ImportErr: 400,
            PredictionError: 500,
            RecommendationError: 500,
            NotFoundError: 404,
            InsufficientTrainingDataError: 422,
        }
        status = status_map.get(type(exc), 500)
        return JSONResponse(
            status_code=status,
            content={"error": type(exc).__name__, "detail": exc.detail, "code": f"FCIP_{status}"},
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
    app.include_router(experiments_router, prefix="/api/experiments", tags=["experiments"])
    app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
    app.include_router(comparisons_router, prefix="/api/compare", tags=["comparisons"])
    app.include_router(predictions_router, prefix="/api/predict", tags=["predictions"])
    app.include_router(recommendations_router, prefix="/api/recommend", tags=["recommendations"])

    return app


app = create_app()
