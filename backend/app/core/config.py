from pathlib import Path
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine base paths: config.py -> core -> app -> backend -> project_root
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "SQL Query Optimizer & Performance Intelligence Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # PostgreSQL Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5434
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "sql_optimizer"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Construct the PostgreSQL connection URI using psycopg3 with safely encoded credentials."""
        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Search for .env in: backend/.env first, then root .env, then current working dir .env
    model_config = SettingsConfigDict(
        env_file=(
            BACKEND_DIR / ".env",
            ROOT_DIR / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
