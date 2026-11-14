"""Checks that protect the scenario contract.

They establish that: the documented example is valid; inputs that would create
a corrupt record are rejected; timestamps are normalised to UTC; and the
committed JSON Schema matches the Python model.
"""

from __future__ import annotations

import copy
import json
from datetime import timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from marinescope.export_schema import SCHEMA_PATH, render_schema
from marinescope.scenario import ScenarioInput

EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "contracts" / "scenario.example.json"




def test_documented_example_is_valid_and_round_trips(example):
    scenario = ScenarioInput.model_validate(example)
    assert [(p.lon, p.lat) for p in scenario.waypoints][0] == (-6.0, 49.5)
    again = ScenarioInput.model_validate_json(scenario.model_dump_json())
    assert again == scenario


def test_departure_time_is_normalised_to_utc(example):
    example["vessel"]["departure_time"] = "2024-06-01T08:00:00+02:00"
    scenario = ScenarioInput.model_validate(example)
    assert scenario.vessel.departure_time.tzinfo == timezone.utc
    assert scenario.vessel.departure_time.hour == 6


def test_names_are_trimmed(example):
    example["name"] = "  Transect A  "
    example["vessel"]["name"] = "	Survey vessel 1 "
    scenario = ScenarioInput.model_validate(example)
    assert (scenario.name, scenario.vessel.name) == ("Transect A", "Survey vessel 1")


def test_name_of_100_characters_with_padding_is_accepted(example):
    example["vessel"]["name"] = " " + "x" * 100 + " "
    assert len(ScenarioInput.model_validate(example).vessel.name) == 100


def _set(data: dict, path: list, value) -> dict:
    data = copy.deepcopy(data)
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return data


INVALID_CASES = [
    ("latitude out of range", ["waypoints", 0, "lat"], 95.0),
    ("longitude out of range (0..360 style)", ["waypoints", 0, "lon"], 354.0),
    ("swapped lon/lat puts waypoint outside region", ["waypoints", 0], {"lon": 49.5, "lat": -6.0}),
    ("waypoint outside region", ["waypoints", 1], {"lon": 10.0, "lat": 48.0}),
    ("only one waypoint", ["waypoints"], [{"lon": -6.0, "lat": 49.5}]),
    (
        "repeated consecutive waypoint",
        ["waypoints"],
        [{"lon": -6.0, "lat": 49.5}, {"lon": -6.0, "lat": 49.5}],
    ),
    ("region west >= east", ["region", "west"], -2.0),
    ("end date before start date", ["data_period", "end_date"], "2024-05-01"),
    ("not a real date", ["data_period", "start_date"], "2024-02-30"),
    ("departure without timezone", ["vessel", "departure_time"], "2024-06-01T06:00:00"),
    ("departure outside data period", ["vessel", "departure_time"], "2024-07-01T06:00:00Z"),
    ("zero speed", ["vessel", "speed_knots"], 0),
    ("zero sampling interval", ["sampling", "interval_minutes"], 0),
    ("negative noise", ["sampling", "noise_std_c"], -0.1),
    ("blank name", ["name"], "   "),
    ("blank vessel name", ["vessel", "name"], "   "),
    ("name too long after trimming", ["name"], "x" * 101),
    ("unknown field", ["colour"], "blue"),
]


@pytest.mark.parametrize("label,path,value", INVALID_CASES, ids=[c[0] for c in INVALID_CASES])
def test_invalid_input_is_rejected(example, label, path, value):
    with pytest.raises(ValidationError):
        ScenarioInput.model_validate(_set(example, path, value))


def test_nan_coordinate_is_rejected(example):
    text = json.dumps(example).replace("-9.0", "NaN", 1)
    with pytest.raises(ValidationError):
        ScenarioInput.model_validate_json(text)


@pytest.mark.parametrize("missing", ["name", "region", "data_period", "vessel", "waypoints", "sampling"])
def test_missing_required_field_is_rejected(example, missing):
    del example[missing]
    with pytest.raises(ValidationError):
        ScenarioInput.model_validate(example)


def test_committed_json_schema_matches_model():
    assert SCHEMA_PATH.read_text(encoding="utf-8") == render_schema(), (
        "contracts/scenario.schema.json is stale; run: python -m marinescope.export_schema"
    )
