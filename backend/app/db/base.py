from sqlalchemy.orm import declarative_base

# Shared declarative base for all SQLAlchemy ORM models
Base = declarative_base()

__all__ = ["Base"]
