"""Serve the downloaded NOAA reference data to the API (MS-06).

"Reference data" is the historical NOAA OISST field: an analysed estimate of
sea surface temperature. It is what reconstructions will later be compared
with. It is not a reconstruction and not perfect ocean truth.

The subset file is produced by marinescope.pipeline.fetch_oisst and lives
outside Git; the manifest that describes it is tracked. Before serving
anything, the file's SHA-256 is compared with the manifest, so the labels shown
in the browser (dataset, dates, units) always describe the file actually read.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import xarray as xr

from . import config


class ReferenceDataUnavailable(Exception):
    """The manifest or the subset file is missing, unreadable or inconsistent."""


@dataclass(frozen=True)
class ReferenceData:
    manifest: dict
    sst: xr.DataArray  # dims (time, lat, lon); NaN where the product has no value

    @property
    def dates(self) -> list[str]:
        return [str(t)[:10] for t in self.sst.time.values]

    def metadata(self) -> dict:
        request = self.manifest["request"]
        dataset = self.manifest["dataset"]
        attributes = dataset["variable_attributes_in_source"]
        west, south, east, north = request["bbox_west_south_east_north"]
        lat = self.sst.lat.values
        return {
            "kind": "reference",
            "description": "Historical analysed sea surface temperature. Reference data, not a reconstruction.",
            "dataset": dataset["name"],
            "product_page": dataset["product_page"],
            "variable": dataset["variable"],
            "long_name": attributes.get("long_name"),
            "units": attributes.get("units"),
            "region": {"west": west, "south": south, "east": east, "north": north},
            "data_period": {"start_date": request["start_date"], "end_date": request["end_date"]},
            "dates": self.dates,
            "grid": {
                "lat_count": int(self.sst.sizes["lat"]),
                "lon_count": int(self.sst.sizes["lon"]),
                "cell_size_degrees": round(float(lat[1] - lat[0]), 6),
                "coordinates": "cell centres, WGS84, longitude -180..180",
            },
            # Range over every day, so one colour scale can be used for all dates.
            "value_range": {
                "min": round(float(self.sst.min()), 2),
                "max": round(float(self.sst.max()), 2),
            },
            "retrieved_at_utc": self.manifest["retrieved_at_utc"],
        }

    def field(self, day: date) -> dict | None:
        """One day's grid, or None if that day is not in the subset.

        values[i][j] belongs to lat[i], lon[j]. Missing cells are null.
        """
        if day.isoformat() not in self.dates:
            return None
        grid = self.sst.isel(time=self.dates.index(day.isoformat()))
        rows = [
            [None if math.isnan(value) else round(value, 2) for value in row]
            for row in grid.values.astype(float).tolist()
        ]
        present = [value for row in rows for value in row if value is not None]
        return {
            "date": day.isoformat(),
            "units": self.manifest["dataset"]["variable_attributes_in_source"].get("units"),
            "lat": [round(float(v), 6) for v in grid.lat.values],
            "lon": [round(float(v), 6) for v in grid.lon.values],
            "values": rows,
            "missing_count": sum(value is None for row in rows for value in row),
            "min": min(present) if present else None,
            "max": max(present) if present else None,
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=2)
def _load(manifest_path: Path, manifest_mtime: float, subset_path: Path, subset_mtime: float) -> ReferenceData:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if _sha256(subset_path) != manifest["subset"]["sha256"]:
        raise ReferenceDataUnavailable(
            "The reference data file does not match its manifest (checksum differs). "
            "Run marinescope.pipeline.fetch_oisst again."
        )
    with xr.open_dataset(subset_path) as dataset:
        sst = dataset["sst"].load()
    return ReferenceData(manifest, sst)


def load() -> ReferenceData:
    """Load (and cache) the reference data named by the current manifest."""
    manifest_path = config.manifest_path()
    if not manifest_path.exists():
        raise ReferenceDataUnavailable(f"The reference data manifest is missing: {manifest_path.name}.")
    try:
        file_name = json.loads(manifest_path.read_text(encoding="utf-8"))["subset"]["file_name"]
    except (ValueError, KeyError) as error:
        raise ReferenceDataUnavailable("The reference data manifest cannot be read.") from error
    subset_path = config.data_dir() / "processed" / file_name
    if not subset_path.exists():
        raise ReferenceDataUnavailable(
            "The reference data has not been downloaded on this machine. "
            "Run marinescope.pipeline.fetch_oisst (see the README)."
        )
    # The modification times are part of the cache key, so a re-download is picked up.
    return _load(manifest_path, manifest_path.stat().st_mtime, subset_path, subset_path.stat().st_mtime)
