"""Alembic migration script template configuration."""

from logging.config import fileConfig

from alembic import context

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Leave target_metadata as None - it's set in env.py
target_metadata = None


def run_migrations_offline() -> None:
    """Run offline migrations."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run online migrations."""
    raise NotImplementedError("Use env.py for async migrations")
