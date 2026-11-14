"""MS-04: scenarios are created, listed and read through the server and database.

Acceptance (Sprint 1 backlog): create/list/read return a valid scenario
consistently; invalid input does not create a record; records survive a
restart of the application.
"""

from __future__ import annotations

import copy
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from marinescope.api import create_app


def count_rows(db) -> int:
    with db.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM scenarios")).scalar()


def test_create_then_read_and_list_return_the_same_scenario(client, example):
    created = client.post("/api/scenarios", json=example)
    assert created.status_code == 201
    body = created.json()
    uuid.UUID(body["id"])
    assert body["created_at"].endswith("Z")

    # Everything the client sent comes back unchanged (plus id and created_at).
    sent_back = {key: body[key] for key in example}
    assert sent_back == example

    read = client.get(f"/api/scenarios/{body['id']}")
    assert read.status_code == 200
    assert read.json() == body

    listed = client.get("/api/scenarios")
    assert listed.status_code == 200
    assert listed.json() == [body]


def test_waypoint_order_and_exact_coordinates_survive_storage(client, example):
    # Awkward decimals and a route that doubles back: order must not be "tidied".
    example["waypoints"] = [
        {"lon": -6.123456789012345, "lat": 49.987654321098765},
        {"lon": -13.5, "lat": 45.5},
        {"lon": -9.000000000000002, "lat": 48.1},
        {"lon": -13.5, "lat": 45.5},
    ]
    created = client.post("/api/scenarios", json=example).json()
    read = client.get(f"/api/scenarios/{created['id']}").json()
    assert read["waypoints"] == example["waypoints"]


def test_lon_lat_are_stored_as_x_y_in_postgis(client, db, example):
    created = client.post("/api/scenarios", json=example).json()
    with db.connect() as connection:
        x, y, srid = connection.execute(
            text("SELECT ST_X(ST_StartPoint(route)), ST_Y(ST_StartPoint(route)), ST_SRID(route) FROM scenarios WHERE id = :id"),
            {"id": created["id"]},
        ).one()
    assert (x, y, srid) == (example["waypoints"][0]["lon"], example["waypoints"][0]["lat"], 4326)


def test_departure_time_is_returned_in_utc(client, example):
    example["vessel"]["departure_time"] = "2024-06-01T08:00:00+02:00"
    created = client.post("/api/scenarios", json=example).json()
    assert created["vessel"]["departure_time"] == "2024-06-01T06:00:00Z"
    assert client.get(f"/api/scenarios/{created['id']}").json()["vessel"]["departure_time"] == "2024-06-01T06:00:00Z"


def test_list_is_newest_first(client, example):
    ids = []
    for name in ("first", "second", "third"):
        example["name"] = name
        ids.append(client.post("/api/scenarios", json=example).json()["id"])
    assert [s["name"] for s in client.get("/api/scenarios").json()] == ["third", "second", "first"]
    assert [s["name"] for s in client.get("/api/scenarios", params={"limit": 2}).json()] == ["third", "second"]


def test_scenario_survives_application_restart(db, database_url, example):
    """A second, completely new application instance reads what the first one saved."""
    first_app = create_app(database_url)
    with TestClient(first_app) as first:
        created = first.post("/api/scenarios", json=example).json()
    first_app.state.engine.dispose()  # every connection of the first instance is closed

    second_app = create_app(database_url)
    with TestClient(second_app) as second:
        assert second.get(f"/api/scenarios/{created['id']}").json() == created
        assert second.get("/api/scenarios").json() == [created]
    second_app.state.engine.dispose()


def _with(data: dict, path: list, value) -> dict:
    data = copy.deepcopy(data)
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return data


INVALID = [
    ("latitude out of range", ["waypoints", 0, "lat"], 95.0, "waypoints.0.lat"),
    ("swapped lon/lat", ["waypoints", 0], {"lon": 49.5, "lat": -6.0}, "scenario"),
    ("impossible date", ["data_period", "start_date"], "2024-02-30", "data_period.start_date"),
    ("end before start", ["data_period", "end_date"], "2024-05-01", "data_period"),
    ("departure without timezone", ["vessel", "departure_time"], "2024-06-01T06:00:00", "vessel.departure_time"),
    ("zero speed", ["vessel", "speed_knots"], 0, "vessel.speed_knots"),
    # Regression: these passed validation, broke a table constraint and gave HTTP 500.
    ("whitespace-only vessel name", ["vessel", "name"], " ", "vessel.name"),
    ("whitespace-only scenario name", ["name"], " 	 ", "name"),
    ("one waypoint", ["waypoints"], [{"lon": -6.0, "lat": 49.5}], "waypoints"),
    ("region outside downloaded data", ["region", "north"], 60.0, "region"),
    ("period outside downloaded data", ["data_period", "end_date"], "2024-06-20", "data_period"),
]


@pytest.mark.parametrize("label,path,value,field", INVALID, ids=[c[0] for c in INVALID])
def test_invalid_scenario_is_rejected_with_a_message_and_not_stored(client, db, example, label, path, value, field):
    response = client.post("/api/scenarios", json=_with(example, path, value))
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["problems"], "the response must say what is wrong"
    assert all(problem["message"] for problem in body["problems"])
    assert field in [problem["field"] for problem in body["problems"]]
    assert count_rows(db) == 0


def test_names_are_stored_trimmed(client, example):
    example["vessel"]["name"] = "  Survey vessel 1  "
    created = client.post("/api/scenarios", json=example)
    assert created.status_code == 201
    assert created.json()["vessel"]["name"] == "Survey vessel 1"
    assert client.get(f"/api/scenarios/{created.json()['id']}").json()["vessel"]["name"] == "Survey vessel 1"


def test_missing_required_field_is_rejected_and_not_stored(client, db, example):
    del example["waypoints"]
    response = client.post("/api/scenarios", json=example)
    assert response.status_code == 422
    assert response.json()["problems"] == [{"field": "waypoints", "message": "Field required"}]
    assert count_rows(db) == 0


def test_body_that_is_not_json_is_rejected(client, db):
    response = client.post("/api/scenarios", content=b"{not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
    assert count_rows(db) == 0


def test_unknown_id_gives_404_and_malformed_id_gives_422(client):
    missing = client.get(f"/api/scenarios/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"] == "not_found"

    malformed = client.get("/api/scenarios/not-a-uuid")
    assert malformed.status_code == 422
    assert malformed.json()["error"] == "validation_error"


INSERT = """
    INSERT INTO scenarios VALUES (
        gen_random_uuid(), now(), 'direct insert',
        -16, 44, -4, 52, '2024-06-01', '2024-06-14',
        'vessel', :speed, now(), 60, 0, 0,
        ST_GeomFromText(:route, 4326)
    )
"""


def test_valid_direct_insert_is_accepted(db):
    """Control for the test below: the INSERT statement itself is sound."""
    with db.begin() as connection:
        connection.execute(text(INSERT), {"speed": 8, "route": "LINESTRING(-6 49.5, -9 48.5)"})
    assert count_rows(db) == 1


@pytest.mark.parametrize(
    "speed,route",
    [
        (0, "LINESTRING(-6 49.5, -9 48.5)"),  # speed must be positive
        (8, "LINESTRING(-6 95, -9 48.5)"),  # latitude 95
        (8, "LINESTRING(354 49.5, 351 48.5)"),  # 0..360 longitudes
    ],
    ids=["zero speed", "latitude 95", "longitude 354"],
)
def test_database_itself_refuses_corrupt_rows(db, speed, route):
    """Defence in depth: the CHECK constraints hold even when the API is bypassed."""
    with pytest.raises(IntegrityError):
        with db.begin() as connection:
            connection.execute(text(INSERT), {"speed": speed, "route": route})
    assert count_rows(db) == 0


def test_database_unavailable_gives_503_not_a_crash(example):
    # Port 1 has no database listening.
    app = create_app("postgresql+psycopg://marinescope:x@127.0.0.1:1/marinescope")
    with TestClient(app) as broken:
        health = broken.get("/api/health")
        assert health.status_code == 200
        assert health.json()["database"] == "unavailable"

        response = broken.post("/api/scenarios", json=example)
        assert response.status_code == 503
        assert response.json()["error"] == "database_unavailable"
    app.state.engine.dispose()
