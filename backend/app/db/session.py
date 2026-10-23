from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.db.base import Base  # re-export Base for backward compatibility and model registration

# Engine configuration prepared for PostgreSQL connection
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args={"connect_timeout": 3} if "postgresql" in settings.SQLALCHEMY_DATABASE_URI else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session and safely closes it upon completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_readiness(timeout: float = 3.0) -> bool:
    """
    Check if the PostgreSQL database is reachable and accepting queries.
    Executes SELECT 1 using a short-lived connection.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            return result == 1
    except Exception:
        return False
