"""
Alembic environment setup for database migrations.

This file configures Alembic to run migrations against the database
defined in the ``DATABASE_URL`` environment variable and uses
``gigi_p2p_telegram_bot.models.Base`` as the metadata for autogeneration.

To generate a new migration revision run:

    alembic revision --autogenerate -m "Your message"

To apply migrations run:

    alembic upgrade head
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from gigi_p2p_telegram_bot import models
from gigi_p2p_telegram_bot.config import DATABASE_URL


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.  This line sets up
# loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Provide target metadata for 'autogenerate' support
target_metadata = models.Base.metadata


def get_url() -> str:
    """Return the database URL from environment variables."""
    url = DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_URL not configured for migrations")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well.  By skipping the
    Engine creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_url()
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = url
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
