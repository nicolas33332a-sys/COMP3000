"""Shared test setup.

API tests run against a real PostgreSQL/PostGIS database, because the things
worth checking (constraints, geometry round trips, survival across restarts)
do not exist in a fake. They use a separate database, ``marinescope_test``,
on the same local server, so the development data is never touched.

Requires the database container: ``docker compose up -d --wait``.
Override the location with TEST_DATABASE_URL.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from marinescope import config
from marinescope.api import create_app

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = config.REPO_ROOT / "contracts" / "scenario.example.json"

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    make_url(config.DEFAULT_DATABASE_URL).set(database="marinescope_test").render_as_string(hide_password=False),
)



def refuse_unsafe_test_database(test_url: str, app_url: str) -> None:
    """Stop before any destructive setup if the tests point at real data.

    The fixtures below empty the scenarios table. That must only ever happen
    in a database whose name ends in "_test" and that is not the one the
    application uses.
    """
    test, application = make_url(test_url), make_url(app_url)
    name = test.database or ""
    same_database = (test.host, test.port or 5432, name) == (
        application.host,
        application.port or 5432,
        application.database,
    )
    if same_database or not name.endswith("_test"):
        raise pytest.UsageError(
            f"Refusing to run: the test database is {name!r} on {test.host}:{test.port or 5432}. "
            'The tests delete data, so TEST_DATABASE_URL must name a database ending in "_test" '
            "that is not the application database."
        )


# Without this, tests hang instead of failing when the database is not running.
FAIL_FAST = {"connect_timeout": 5}


@pytest.fixture
def example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def database_url() -> str:
    """Create the test database if needed and bring it to the latest migration."""
    refuse_unsafe_test_database(TEST_DATABASE_URL, config.database_url())
    url = make_url(TEST_DATABASE_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT", connect_args=FAIL_FAST)
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    alembic_config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(alembic_config, "head")  # also proves the migration runs from empty
    return TEST_DATABASE_URL


@pytest.fixture
def db(database_url):
    """An engine on an empty scenarios table."""
    engine = create_engine(database_url, connect_args=FAIL_FAST)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE scenarios"))
    yield engine
    engine.dispose()


@pytest.fixture
def client(db, database_url):
    app = create_app(database_url)
    with TestClient(app) as test_client:
        yield test_client
    app.state.engine.dispose()
