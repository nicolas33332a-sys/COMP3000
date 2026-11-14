"""Store and load scenarios. The only module that touches the scenarios table.

It converts between the API shape (marinescope.scenario) and the table row
(marinescope.models), so the rest of the code never handles rows directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import LineString
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ScenarioRow
from .scenario import Scenario, ScenarioInput


def _to_scenario(row: ScenarioRow) -> Scenario:
    # LineString coordinates come back as (x, y) = (lon, lat) in stored order.
    waypoints = [{"lon": lon, "lat": lat} for lon, lat in to_shape(row.route).coords]
    # Building a Scenario re-runs validation, so a row that somehow broke the
    # contract fails loudly here instead of being served to the browser.
    return Scenario.model_validate(
        {
            "id": row.id,
            "created_at": row.created_at,
            "name": row.name,
            "region": {
                "west": row.region_west,
                "south": row.region_south,
                "east": row.region_east,
                "north": row.region_north,
            },
            "data_period": {"start_date": row.data_start_date, "end_date": row.data_end_date},
            "vessel": {
                "name": row.vessel_name,
                "speed_knots": row.vessel_speed_knots,
                "departure_time": row.vessel_departure_time,
            },
            "waypoints": waypoints,
            "sampling": {
                "interval_minutes": row.sampling_interval_minutes,
                "noise_std_c": row.sampling_noise_std_c,
                "random_seed": row.sampling_random_seed,
            },
        }
    )


def create_scenario(session: Session, data: ScenarioInput) -> Scenario:
    row = ScenarioRow(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        name=data.name,
        region_west=data.region.west,
        region_south=data.region.south,
        region_east=data.region.east,
        region_north=data.region.north,
        data_start_date=data.data_period.start_date,
        data_end_date=data.data_period.end_date,
        vessel_name=data.vessel.name,
        vessel_speed_knots=data.vessel.speed_knots,
        vessel_departure_time=data.vessel.departure_time,
        sampling_interval_minutes=data.sampling.interval_minutes,
        sampling_noise_std_c=data.sampling.noise_std_c,
        sampling_random_seed=data.sampling.random_seed,
        route=from_shape(LineString([(p.lon, p.lat) for p in data.waypoints]), srid=4326),
    )
    session.add(row)
    session.commit()
    session.refresh(row)  # read back what the database actually stored
    return _to_scenario(row)


def list_scenarios(session: Session, limit: int = 100) -> list[Scenario]:
    """Newest first."""
    query = select(ScenarioRow).order_by(ScenarioRow.created_at.desc(), ScenarioRow.id).limit(limit)
    return [_to_scenario(row) for row in session.scalars(query)]


def get_scenario(session: Session, scenario_id: uuid.UUID) -> Scenario | None:
    row = session.get(ScenarioRow, scenario_id)
    return _to_scenario(row) if row else None
