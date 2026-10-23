from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import check_db_readiness
from app.schemas.health import HealthResponse, ReadinessResponse, RootResponse
from app.api.analysis import router as analysis_router
from app.api.benchmarks import router as benchmarks_router
from app.api.validation import router as validation_router
from app.api.evaluations import router as evaluations_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local development (frontend support on Vite default ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register API v1 routers
app.include_router(analysis_router, prefix=settings.API_V1_STR)
app.include_router(benchmarks_router, prefix=settings.API_V1_STR)
app.include_router(validation_router, prefix=settings.API_V1_STR)
app.include_router(evaluations_router, prefix=settings.API_V1_STR)


@app.get("/", response_model=RootResponse, tags=["General"])
def root() -> RootResponse:
    """Root endpoint confirming that the API service is active."""
    return RootResponse(
        message=f"Welcome to {settings.PROJECT_NAME}",
        docs_url="/docs",
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check() -> HealthResponse:
    """Application liveness check confirming the HTTP API is operational."""
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version="0.1.0",
    )


@app.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "Application and Database are healthy and ready."},
        503: {"description": "Database is unavailable or not accepting queries."},
    },
    tags=["Health"],
)
def readiness_check(response: Response) -> ReadinessResponse:
    """
    Database readiness check confirming PostgreSQL connectivity.
    Returns HTTP 200 when database responds, HTTP 503 Service Unavailable when unreachable.
    """
    is_ready = check_db_readiness()
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="unhealthy",
            database="disconnected",
            environment=settings.ENVIRONMENT,
            version="0.1.0",
            detail="Database connection check failed or timed out.",
        )

    return ReadinessResponse(
        status="healthy",
        database="connected",
        environment=settings.ENVIRONMENT,
        version="0.1.0",
        detail=None,
    )
