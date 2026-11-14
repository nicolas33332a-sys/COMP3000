"""Inspect the pilot OISST subset and draw a reference plot.

Example (from the backend folder, after fetch_oisst):

    python -m marinescope.pipeline.inspect_oisst

Reads the subset named in manifests/oisst-pilot-manifest.json, verifies its
checksum, then records dates, units, coordinates, array shapes and the
land/missing mask in docs/evaluation/s01-oisst-pilot/inspection.json (a local,
Git-ignored folder) and
draws reference_plot.png next to it.

This is a technical check that the data path works. It says nothing about
reconstruction accuracy.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display needed
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from . import REPO_ROOT, data_dir
from .fetch_oisst import DEFAULT_MANIFEST, sha256_of

DEFAULT_OUT = REPO_ROOT / "docs" / "evaluation" / "s01-oisst-pilot"
EXAMPLE_SCENARIO = REPO_ROOT / "contracts" / "scenario.example.json"


def cell_edges(centres: np.ndarray) -> np.ndarray:
    step = float(np.diff(centres).mean())
    return np.concatenate([centres - step / 2, [centres[-1] + step / 2]])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    subset_path = data_dir() / "processed" / manifest["subset"]["file_name"]
    if not subset_path.exists():
        raise SystemExit(f"Subset not found: {subset_path}\nRun marinescope.pipeline.fetch_oisst first.")
    checksum_ok = sha256_of(subset_path) == manifest["subset"]["sha256"]

    ds = xr.open_dataset(subset_path).load()
    sst = ds["sst"]
    values = sst.values  # (time, lat, lon), NaN where the product has no SST
    missing = np.isnan(values)
    lat, lon = ds.lat.values, ds.lon.values
    dates = [str(t)[:10] for t in ds.time.values]
    day_gaps = np.diff(ds.time.values).astype("timedelta64[h]").astype(int)

    report = {
        "purpose": "Technical pilot inspection (backlog MS-03). Not accuracy evidence.",
        "subset_file": subset_path.name,
        "subset_checksum_matches_manifest": bool(checksum_ok),
        "dimension_order": list(sst.dims),
        "shape": list(values.shape),
        "dtype_in_memory": str(values.dtype),
        "units": sst.attrs.get("units"),
        "long_name": sst.attrs.get("long_name"),
        "time": {
            "count": len(dates),
            "first": dates[0],
            "last": dates[-1],
            "timestamps_first_last": [str(ds.time.values[0])[:19], str(ds.time.values[-1])[:19]],
            "all_steps_24h": bool((day_gaps == 24).all()),
            "matches_requested_period": dates[0] == manifest["request"]["start_date"]
            and dates[-1] == manifest["request"]["end_date"],
        },
        "lat": {
            "count": int(lat.size), "first": float(lat[0]), "last": float(lat[-1]),
            "step": float(np.diff(lat).mean()), "ascending": bool((np.diff(lat) > 0).all()),
        },
        "lon": {
            "count": int(lon.size), "first": float(lon[0]), "last": float(lon[-1]),
            "step": float(np.diff(lon).mean()), "ascending": bool((np.diff(lon) > 0).all()),
            "convention": "-180..180",
        },
        "missing_mask": {
            "cells_per_day": int(missing[0].size),
            "missing_cells_per_day": [int(m.sum()) for m in missing],
            "mask_identical_every_day": bool((missing == missing[0]).all()),
            "missing_fraction_day_1": round(float(missing[0].mean()), 4),
            "interpretation": "Missing cells are where OISST provides no SST; in this box "
            "that is expected to be land. Compare the mask panel of the plot with the coastline.",
        },
        "sst_valid_cells_c": {
            "min": round(float(np.nanmin(values)), 2),
            "max": round(float(np.nanmax(values)), 2),
            "mean": round(float(np.nanmean(values)), 2),
            "daily_mean": [round(float(np.nanmean(v)), 2) for v in values],
        },
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "inspection.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    # Reference plot: first day's field with the example route, plus the mask.
    lon_e, lat_e = cell_edges(lon), cell_edges(lat)
    fig, (ax_sst, ax_mask) = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#d9d9d9")
    mesh = ax_sst.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(values[0]), cmap=cmap, shading="flat")
    fig.colorbar(mesh, ax=ax_sst, label="Sea surface temperature (°C)")
    ax_sst.set_title(f"NOAA OISST v2.1 daily SST, {dates[0]} (UTC day)")
    if EXAMPLE_SCENARIO.exists():
        route = json.loads(EXAMPLE_SCENARIO.read_text(encoding="utf-8"))["waypoints"]
        ax_sst.plot([p["lon"] for p in route], [p["lat"] for p in route], "o-", color="white",
                    markeredgecolor="black", linewidth=1.5, label="Example scenario route")
        ax_sst.legend(loc="lower left", fontsize=8)
    ax_mask.pcolormesh(lon_e, lat_e, missing[0].astype(float), cmap="Greys", vmin=0, vmax=1.6, shading="flat")
    ax_mask.set_title(f"Missing-value mask (grey = no SST; {int(missing[0].sum())} of {missing[0].size} cells)")
    for ax in (ax_sst, ax_mask):
        ax.set_xlabel("Longitude (°E, WGS84)")
        ax.set_ylabel("Latitude (°N, WGS84)")
        ax.set_aspect(1 / np.cos(np.deg2rad(lat.mean())))
    fig.suptitle(
        "Reference data pilot — 0.25° grid, grey = no SST value (land). "
        "Source: NOAA NCEI OISST v2.1. Reference field, not a reconstruction.",
        fontsize=9,
    )
    fig.savefig(args.out_dir / "reference_plot.png", dpi=130)

    print(json.dumps(report, indent=2))
    print(f"Wrote {args.out_dir / 'inspection.json'} and reference_plot.png")
    if not checksum_ok:
        raise SystemExit("Subset checksum does not match the manifest.")


if __name__ == "__main__":
    main()
