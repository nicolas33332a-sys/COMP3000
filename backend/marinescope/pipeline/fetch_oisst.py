"""Download daily NOAA OISST v2.1 files and cut a small regional subset.

Example (from the backend folder):

    python -m marinescope.pipeline.fetch_oisst --start 2024-06-01 --end 2024-06-14 \
        --bbox -16 44 -4 52

What it does:
1. Downloads one global NetCDF file per day from NOAA NCEI (about 1.5 MB each)
   into <data dir>/raw/oisst-v2.1/. Files already present are not re-downloaded.
2. Converts longitude from the product's 0..360 convention to MarineScope's
   -180..180 convention and selects the requested box.
3. Writes the subset to <data dir>/processed/ and a provenance manifest
   (source URLs, sizes, SHA-256 checksums, retrieval time, tool versions).

The manifest is small and is committed; the data files are not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import xarray as xr

from . import REPO_ROOT, data_dir

BASE_URL = (
    "https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation/"
    "v2.1/access/avhrr"
)
PRODUCT_PAGE = "https://www.ncei.noaa.gov/products/optimum-interpolation-sst"
DEFAULT_MANIFEST = REPO_ROOT / "manifests" / "oisst-pilot-manifest.json"
USER_AGENT = "MarineScope-data-pipeline (student project; urllib)"


def file_url(day: date) -> str:
    return f"{BASE_URL}/{day:%Y%m}/oisst-avhrr-v02r01.{day:%Y%m%d}.nc"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> bool:
    """Download url to dest unless it already exists. Returns True if fetched."""
    if dest.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as out:
        shutil.copyfileobj(response, out)
    partial.replace(dest)
    return True


def subset_day(path: Path, west: float, south: float, east: float, north: float) -> xr.Dataset:
    """Open one global daily file and return the SST box with lon in -180..180."""
    with xr.open_dataset(path) as ds:
        lon_min, lon_max = float(ds.lon.min()), float(ds.lon.max())
        if lon_min < 0 or lon_max <= 180:
            raise ValueError(f"Expected 0..360 longitudes in {path.name}, got {lon_min}..{lon_max}")
        ds = ds.assign_coords(lon=((ds.lon + 180) % 360) - 180).sortby("lon")
        box = ds[["sst"]].sel(lat=slice(south, north), lon=slice(west, east))
        # zlev is a single surface level (0 m); drop the length-1 dimension.
        return box.squeeze("zlev", drop=True).load()


def jsonable(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=date.fromisoformat, required=True, help="First UTC day, YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, required=True, help="Last UTC day (inclusive)")
    parser.add_argument(
        "--bbox", type=float, nargs=4, required=True, metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        help="Box in degrees, longitudes -180..180",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Where to write the manifest")
    args = parser.parse_args()

    west, south, east, north = args.bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        parser.error("bbox must satisfy -180 <= WEST < EAST <= 180 and -90 <= SOUTH < NORTH <= 90")
    if args.end < args.start:
        parser.error("--end must not be before --start")
    days = [args.start + timedelta(days=n) for n in range((args.end - args.start).days + 1)]
    if len(days) > 62:
        parser.error("Refusing to download more than 62 daily files in one pilot run")

    raw_dir = data_dir() / "raw" / "oisst-v2.1"
    processed_dir = data_dir() / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    files, pieces, source_attrs, sst_attrs, sst_encoding = [], [], {}, {}, {}
    for day in days:
        url = file_url(day)
        dest = raw_dir / url.rsplit("/", 1)[1]
        fetched = download(url, dest)
        print(f"{'downloaded' if fetched else 'cached    '} {dest.name}")
        files.append({"url": url, "bytes": dest.stat().st_size, "sha256": sha256_of(dest)})
        pieces.append(subset_day(dest, west, south, east, north))
        if not source_attrs:
            with xr.open_dataset(dest) as ds:
                source_attrs = {k: jsonable(v) for k, v in ds.attrs.items()}
                sst_attrs = {k: jsonable(v) for k, v in ds.sst.attrs.items()}
                sst_encoding = {
                    k: jsonable(v)
                    for k, v in ds.sst.encoding.items()
                    if k in ("dtype", "scale_factor", "add_offset", "_FillValue")
                }
                sst_encoding["dtype"] = str(sst_encoding.get("dtype"))

    subset = xr.concat(pieces, dim="time")
    subset.attrs = {
        "title": "MarineScope pilot subset of NOAA OISST v2.1 daily SST",
        "source": PRODUCT_PAGE,
        "longitude_convention": "-180..180 (converted from the product's 0..360)",
        "note": "Derived regional subset for a technical pilot. See the manifest for provenance.",
    }
    stem = f"oisst-v2.1_sst_{args.start:%Y%m%d}-{args.end:%Y%m%d}_pilot"
    subset_path = processed_dir / f"{stem}.nc"
    subset.to_netcdf(subset_path)

    manifest = {
        "manifest_version": 1,
        "purpose": "Technical pilot (backlog MS-03). Not scientific accuracy evidence.",
        "dataset": {
            "name": "NOAA 1/4 degree Daily Optimum Interpolation Sea Surface Temperature (OISST), Version 2.1",
            "product_page": PRODUCT_PAGE,
            "access_base_url": BASE_URL,
            "variable": "sst",
            "variable_attributes_in_source": sst_attrs,
            "variable_packing_in_source": sst_encoding,
            "global_attributes_of_first_source_file": source_attrs,
        },
        "request": {
            "start_date": args.start.isoformat(),
            "end_date": args.end.isoformat(),
            "bbox_west_south_east_north": [west, south, east, north],
            "date_convention": "UTC days, inclusive",
            "longitude_convention": "-180..180 after conversion from 0..360",
        },
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_files": files,
        "subset": {
            "file_name": subset_path.name,
            "location": "<MARINESCOPE_DATA_DIR>/processed/ (not in Git)",
            "bytes": subset_path.stat().st_size,
            "sha256": sha256_of(subset_path),
            "dims": {name: int(size) for name, size in subset.sizes.items()},
            "lat_first_last": [float(subset.lat[0]), float(subset.lat[-1])],
            "lon_first_last": [float(subset.lon[0]), float(subset.lon[-1])],
            "time_first_last": [str(subset.time.values[0])[:19], str(subset.time.values[-1])[:19]],
        },
        "tools": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "xarray": xr.__version__,
            "command": "python -m marinescope.pipeline.fetch_oisst "
            f"--start {args.start} --end {args.end} --bbox {west:g} {south:g} {east:g} {north:g}",
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, indent=2) + "\n"
    args.manifest.write_text(text, encoding="utf-8", newline="\n")
    (processed_dir / f"{stem}.manifest.json").write_text(text, encoding="utf-8", newline="\n")
    print(f"Subset:   {subset_path}  dims={dict(subset.sizes)}")
    print(f"Manifest: {args.manifest}")


if __name__ == "__main__":
    main()
