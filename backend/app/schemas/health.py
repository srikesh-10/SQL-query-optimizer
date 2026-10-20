from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str


class RootResponse(BaseModel):
    message: str
    docs_url: str
