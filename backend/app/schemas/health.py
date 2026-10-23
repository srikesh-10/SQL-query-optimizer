from typing import Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    database: str
    environment: str
    version: str
    detail: Optional[str] = None


class RootResponse(BaseModel):
    message: str
    docs_url: str
