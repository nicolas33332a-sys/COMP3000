"""NOAA OISST data pipeline: download, subset, inspect."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def data_dir() -> Path:
    """Where large downloaded/derived data lives. Never committed to Git."""
    return Path(os.environ.get("MARINESCOPE_DATA_DIR", REPO_ROOT / "data")).resolve()
