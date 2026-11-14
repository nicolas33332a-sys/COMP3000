"""Runtime settings, read from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Matches docker-compose.yml. A local development default, not a secret.
DEFAULT_DATABASE_URL = "postgresql+psycopg://marinescope:marinescope-local@127.0.0.1:5432/marinescope"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def manifest_path() -> Path:
    """The provenance manifest describing which reference data is available."""
    default = REPO_ROOT / "manifests" / "oisst-pilot-manifest.json"
    return Path(os.environ.get("MARINESCOPE_MANIFEST", default))
