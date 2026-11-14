"""MS-06: the API serves the reference temperature field with correct labels.

Most tests use a tiny SYNTHETIC grid written to a temporary folder. It exists
only to check the mechanics (orientation, missing cells, dates, checksum) with
values that are easy to reason about. It is not NOAA data.

One test at the end reads the real downloaded NOAA subset and is skipped on
machines (such as CI) where it has not been downloaded.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest
import xarray as xr
from fastapi.testclient import TestClient

from marinescope import config
from marinescope.api import create_app

# Synthetic grid: 2 latitudes x 3 longitudes, 2 days. value = 10*lat_index + lon_index (+100 on day 2).
LAT = [44.125, 44.375]
LON = [-15.875, -15.625, -15.375]
DAY_1 = [[0.0, 1.0, 2.0], [10.0, np.nan, 12.0]]  # one missing cell at lat[1], lon[1]


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    """Write a synthetic subset + manifest and point the app at them."""
    values = np.array([DAY_1, (np.array(DAY_1) + 100).tolist()], dtype="float32")
    dataset = xr.Dataset(
        {"sst": (("time", "lat", "lon"), values)},
        coords={"time": np.array(["2024-06-01T12:00", "2024-06-02T12:00"], dtype="datetime64[ns]"), "lat": LAT, "lon": LON},
    )
    processed = tmp_path / "processed"
    processed.mkdir()
    subset = processed / "synthetic.nc"
    dataset.to_netcdf(subset)
    manifest = {
        "dataset": {
            "name": "SYNTHETIC TEST GRID (not NOAA data)",
            "product_page": "https://example.invalid/",
            "variable": "sst",
            "variable_attributes_in_source": {"long_name": "Synthetic", "units": "Celsius"},
        },
        "request": {
            "start_date": "2024-06-01",
            "end_date": "2024-06-02",
            "bbox_west_south_east_north": [-16.0, 44.0, -15.25, 44.5],
        },
        "retrieved_at_utc": "2024-01-01T00:00:00+00:00",
        "subset": {"file_name": subset.name, "sha256": hashlib.sha256(subset.read_bytes()).hexdigest()},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setenv("MARINESCOPE_MANIFEST", str(manifest_path))
    monkeypatch.setenv("MARINESCOPE_DATA_DIR", str(tmp_path))
    return {"subset": subset, "manifest_path": manifest_path, "manifest": manifest}


@pytest.fixture
def api():
    # These endpoints never touch the database, so no database fixture is needed.
    app = create_app()
    with TestClient(app) as client:
        yield client
    app.state.engine.dispose()


def test_metadata_labels_come_from_the_manifest(api, synthetic):
    body = api.get("/api/reference-data").json()
    assert body["kind"] == "reference"
    assert body["dataset"] == "SYNTHETIC TEST GRID (not NOAA data)"
    assert body["units"] == "Celsius"
    assert body["region"] == {"west": -16.0, "south": 44.0, "east": -15.25, "north": 44.5}
    assert body["data_period"] == {"start_date": "2024-06-01", "end_date": "2024-06-02"}
    assert body["dates"] == ["2024-06-01", "2024-06-02"]
    assert body["grid"]["lat_count"] == 2 and body["grid"]["lon_count"] == 3
    assert body["grid"]["cell_size_degrees"] == 0.25
    assert body["value_range"] == {"min": 0.0, "max": 112.0}


def test_field_orientation_is_values_lat_lon_and_missing_is_null(api, synthetic):
    body = api.get("/api/reference-data/sst", params={"date": "2024-06-01"}).json()
    assert body["date"] == "2024-06-01"
    assert body["units"] == "Celsius"
    assert body["lat"] == LAT and body["lon"] == LON
    # values[i][j] is at lat[i], lon[j]
    assert body["values"] == [[0.0, 1.0, 2.0], [10.0, None, 12.0]]
    assert body["missing_count"] == 1
    assert (body["min"], body["max"]) == (0.0, 12.0)


def test_each_date_returns_its_own_field(api, synthetic):
    second = api.get("/api/reference-data/sst", params={"date": "2024-06-02"}).json()
    assert second["date"] == "2024-06-02"
    assert second["values"][0] == [100.0, 101.0, 102.0]


def test_date_outside_the_data_gives_404_and_bad_date_gives_422(api, synthetic):
    outside = api.get("/api/reference-data/sst", params={"date": "2024-06-03"})
    assert outside.status_code == 404
    assert outside.json()["error"] == "not_found"

    for bad in ({"date": "2024-02-30"}, {"date": "yesterday"}, {}):
        response = api.get("/api/reference-data/sst", params=bad)
        assert response.status_code == 422
        assert response.json()["problems"]


def test_file_that_does_not_match_its_manifest_is_not_served(api, synthetic):
    synthetic["manifest"]["subset"]["sha256"] = "0" * 64
    synthetic["manifest_path"].write_text(json.dumps(synthetic["manifest"]), encoding="utf-8")
    response = api.get("/api/reference-data/sst", params={"date": "2024-06-01"})
    assert response.status_code == 503
    assert response.json()["error"] == "reference_data_unavailable"
    assert "checksum" in response.json()["message"]


def test_missing_data_file_gives_a_clear_503(api, synthetic):
    synthetic["subset"].unlink()
    for path in ("/api/reference-data", "/api/reference-data/sst?date=2024-06-01"):
        response = api.get(path)
        assert response.status_code == 503
        assert response.json()["error"] == "reference_data_unavailable"
        assert "not been downloaded" in response.json()["message"]


def test_missing_manifest_gives_503_for_reference_data_and_for_creating_scenarios(api, synthetic, example):
    synthetic["manifest_path"].unlink()
    assert api.get("/api/reference-data").status_code == 503
    created = api.post("/api/scenarios", json=example)
    assert created.status_code == 503
    assert created.json()["error"] == "reference_data_unavailable"


def test_real_noaa_subset_matches_its_manifest(api):
    """Reads the real downloaded data. Skipped where it has not been downloaded."""
    manifest = json.loads(config.manifest_path().read_text(encoding="utf-8"))
    if not (config.data_dir() / "processed" / manifest["subset"]["file_name"]).exists():
        pytest.skip("NOAA subset not downloaded on this machine (run marinescope.pipeline.fetch_oisst)")

    meta = api.get("/api/reference-data").json()
    assert meta["dataset"] == manifest["dataset"]["name"]
    assert meta["units"] == manifest["dataset"]["variable_attributes_in_source"]["units"] == "Celsius"
    assert meta["dates"][0] == manifest["request"]["start_date"]
    assert meta["dates"][-1] == manifest["request"]["end_date"]
    assert len(meta["dates"]) == manifest["subset"]["dims"]["time"]

    field = api.get("/api/reference-data/sst", params={"date": meta["dates"][0]}).json()
    assert len(field["values"]) == manifest["subset"]["dims"]["lat"] == len(field["lat"])
    assert len(field["values"][0]) == manifest["subset"]["dims"]["lon"] == len(field["lon"])
    assert [field["lat"][0], field["lat"][-1]] == manifest["subset"]["lat_first_last"]
    assert [field["lon"][0], field["lon"][-1]] == manifest["subset"]["lon_first_last"]
    west, south, east, north = manifest["request"]["bbox_west_south_east_north"]
    assert west < field["lon"][0] and field["lon"][-1] < east
    assert south < field["lat"][0] and field["lat"][-1] < north
