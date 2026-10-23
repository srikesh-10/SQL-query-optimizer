from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import pool, engine_from_config
from alembic import context

# Ensure backend root is in sys.path so app modules import cleanly
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Import application settings and ORM Base metadata
from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401 - register models on Base.metadata

# Alembic Config object
config = context.config

# Interpret the config file for Python logging if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set SQLAlchemy URL dynamically from settings (avoids hardcoding in alembic.ini)
config.set_main_option("sqlalchemy.url", settings.SQLALCHEMY_DATABASE_URI)

# Bind SQLAlchemy ORM Base metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode without an active DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with an active engine connection."""
    # Use existing database session engine configuration directly or create from section
    from app.db.session import engine

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
