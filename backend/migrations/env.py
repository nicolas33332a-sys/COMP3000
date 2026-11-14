"""Alembic entry point: connects to the database and runs the migrations."""

from alembic import context
from sqlalchemy import create_engine

from marinescope import config as app_config

# Tests pass their own URL; otherwise use DATABASE_URL / the local default.
url = context.config.get_main_option("sqlalchemy.url") or app_config.database_url()

engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
