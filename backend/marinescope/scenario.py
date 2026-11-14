"""The minimal scenario contract (backlog MS-03 slice, used by MS-04 onwards).

This module is the single source of truth for the scenario shape. The JSON
Schema in contracts/scenario.schema.json is generated from it, and the
TypeScript types in frontend/src/scenario.ts mirror it by hand.

Conventions:

* Coordinates are WGS84 decimal degrees. Longitude is -180..180 (east
  positive), latitude is -90..90 (north positive). Fields are always named
  ``lon`` / ``lat``; where a bare pair is unavoidable (GeoJSON, MapLibre) the
  order is [lon, lat].
* Dates are ISO 8601 calendar dates (YYYY-MM-DD) and mean UTC days, matching
  the daily NOAA OISST product. Both ends of a period are inclusive.
* Timestamps are ISO 8601 with an explicit offset and are normalised to UTC.
* Units are carried in field names: knots, minutes, degrees Celsius (``_c``).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

MIN_WAYPOINTS = 2
MAX_WAYPOINTS = 100

Longitude = Annotated[float, Field(ge=-180, le=180, description="Degrees east, WGS84, -180..180")]
Latitude = Annotated[float, Field(ge=-90, le=90, description="Degrees north, WGS84, -90..90")]


class _Strict(BaseModel):
    """Reject unknown fields and NaN/Infinity so bad input cannot be stored."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Waypoint(_Strict):
    lon: Longitude
    lat: Latitude


class RegionBounds(_Strict):
    """Axis-aligned box. Boxes that cross the antimeridian are not supported."""

    west: Longitude
    south: Latitude
    east: Longitude
    north: Latitude

    @model_validator(mode="after")
    def _ordered(self) -> RegionBounds:
        if self.west >= self.east:
            raise ValueError("region.west must be less than region.east")
        if self.south >= self.north:
            raise ValueError("region.south must be less than region.north")
        return self

    def contains(self, point: Waypoint) -> bool:
        return self.west <= point.lon <= self.east and self.south <= point.lat <= self.north


class DataPeriod(_Strict):
    """Historical reference-data period in UTC days, inclusive at both ends."""

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _ordered(self) -> DataPeriod:
        if self.end_date < self.start_date:
            raise ValueError("data_period.end_date must not be before start_date")
        return self


class VesselSettings(_Strict):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    speed_knots: Annotated[float, Field(gt=0, le=50, description="Constant speed over ground, knots")]
    departure_time: Annotated[
        AwareDatetime,
        Field(description="When the vessel leaves the first waypoint. ISO 8601 with offset; stored as UTC"),
    ]

    @field_validator("departure_time")
    @classmethod
    def _to_utc(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class SamplingSettings(_Strict):
    interval_minutes: Annotated[int, Field(ge=1, le=1440, description="Time between simulated readings")]
    noise_std_c: Annotated[
        float, Field(ge=0, le=5, description="Std. dev. of simulated sensor noise, degrees Celsius")
    ] = 0.0
    random_seed: Annotated[int, Field(ge=0, le=2**31 - 1, description="Seed for reproducible noise")] = 0


class ScenarioInput(_Strict):
    """What a client submits to create a scenario."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    region: RegionBounds
    data_period: DataPeriod
    vessel: VesselSettings
    waypoints: Annotated[
        list[Waypoint],
        Field(min_length=MIN_WAYPOINTS, max_length=MAX_WAYPOINTS, description="Route in visiting order"),
    ]
    sampling: SamplingSettings

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> ScenarioInput:
        for index, point in enumerate(self.waypoints):
            if not self.region.contains(point):
                raise ValueError(f"waypoints[{index}] lies outside the region bounds")
        for index in range(1, len(self.waypoints)):
            if self.waypoints[index] == self.waypoints[index - 1]:
                raise ValueError(f"waypoints[{index}] repeats the previous waypoint")
        departure_day = self.vessel.departure_time.date()  # already UTC
        if not (self.data_period.start_date <= departure_day <= self.data_period.end_date):
            raise ValueError("vessel.departure_time must fall inside data_period (UTC days)")
        return self


class Scenario(ScenarioInput):
    """A stored scenario: the input plus server-assigned fields (used from MS-04)."""

    id: UUID
    created_at: AwareDatetime
