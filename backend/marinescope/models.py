"""Database table for scenarios (SQLAlchemy).

The table itself is created by the migration in backend/migrations/, which
also holds the CHECK constraints. This class only tells SQLAlchemy how to
read and write rows.

The route is one PostGIS LineString in WGS84 (SRID 4326). Its points are the
waypoints in visiting order, each stored as (lon, lat) - PostGIS x is
longitude and y is latitude, the same order as the rest of MarineScope.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import Date, DateTime, Float, Integer, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ScenarioRow(Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    name: Mapped[str] = mapped_column(String(100))

    region_west: Mapped[float] = mapped_column(Float)
    region_south: Mapped[float] = mapped_column(Float)
    region_east: Mapped[float] = mapped_column(Float)
    region_north: Mapped[float] = mapped_column(Float)

    data_start_date: Mapped[date] = mapped_column(Date)
    data_end_date: Mapped[date] = mapped_column(Date)

    vessel_name: Mapped[str] = mapped_column(String(100))
    vessel_speed_knots: Mapped[float] = mapped_column(Float)
    vessel_departure_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    sampling_interval_minutes: Mapped[int] = mapped_column(Integer)
    sampling_noise_std_c: Mapped[float] = mapped_column(Float)
    sampling_random_seed: Mapped[int] = mapped_column(Integer)

    route: Mapped[WKBElement] = mapped_column(Geometry("LINESTRING", srid=4326, spatial_index=False))
