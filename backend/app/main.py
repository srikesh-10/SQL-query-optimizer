from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.schemas.health import HealthResponse, RootResponse

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local development (frontend support)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=RootResponse, tags=["General"])
def root() -> RootResponse:
    """Root endpoint confirming that the API service is active."""
    return RootResponse(
        message=f"Welcome to {settings.PROJECT_NAME}",
        docs_url="/docs",
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check() -> HealthResponse:
    """Health check endpoint returning API operational status."""
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version="0.1.0",
    )
