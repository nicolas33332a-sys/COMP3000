"""Runtime settings, read from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]

# Read <repository>/.env if it exists, so the API, alembic, the tests and
# docker compose (which reads the same file itself) all see the same values.
# Variables already set in the real environment win over the file.
load_dotenv(REPO_ROOT / ".env")

# Matches docker-compose.yml, including its MARINESCOPE_DB_PORT override.
# A local development default, not a secret.
DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://marinescope:marinescope-local@127.0.0.1:"
    f"{os.environ.get('MARINESCOPE_DB_PORT', '5432')}/marinescope"
)


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def manifest_path() -> Path:
    """The provenance manifest describing which reference data is available."""
    default = REPO_ROOT / "manifests" / "oisst-pilot-manifest.json"
    return Path(os.environ.get("MARINESCOPE_MANIFEST", default))
