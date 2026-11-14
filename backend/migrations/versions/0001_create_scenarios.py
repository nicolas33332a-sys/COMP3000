"""Create the scenarios table.

Revision ID: 0001
Revises:

Written as plain SQL so the table can be read directly. The CHECK constraints
repeat the most important rules from marinescope/scenario.py: even if a bug
or a manual INSERT bypassed the API, the database refuses a corrupt record.
"""

from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute(
        """
        CREATE TABLE scenarios (
            id                        uuid PRIMARY KEY,
            created_at                timestamptz NOT NULL,
            name                      varchar(100) NOT NULL CHECK (btrim(name) <> ''),

            region_west               double precision NOT NULL CHECK (region_west  BETWEEN -180 AND 180),
            region_south              double precision NOT NULL CHECK (region_south BETWEEN -90 AND 90),
            region_east               double precision NOT NULL CHECK (region_east  BETWEEN -180 AND 180),
            region_north              double precision NOT NULL CHECK (region_north BETWEEN -90 AND 90),
            CHECK (region_west < region_east),
            CHECK (region_south < region_north),

            data_start_date           date NOT NULL,
            data_end_date             date NOT NULL,
            CHECK (data_start_date <= data_end_date),

            vessel_name               varchar(100) NOT NULL CHECK (btrim(vessel_name) <> ''),
            vessel_speed_knots        double precision NOT NULL
                CHECK (vessel_speed_knots > 0 AND vessel_speed_knots <= 50),
            vessel_departure_time     timestamptz NOT NULL,

            sampling_interval_minutes integer NOT NULL CHECK (sampling_interval_minutes BETWEEN 1 AND 1440),
            sampling_noise_std_c      double precision NOT NULL CHECK (sampling_noise_std_c BETWEEN 0 AND 5),
            sampling_random_seed      integer NOT NULL CHECK (sampling_random_seed >= 0),

            -- Waypoints in visiting order; x = longitude, y = latitude (WGS84).
            route                     geometry(LineString, 4326) NOT NULL
                CHECK (ST_NPoints(route) BETWEEN 2 AND 100)
                CHECK (ST_XMin(route) >= -180 AND ST_XMax(route) <= 180
                       AND ST_YMin(route) >= -90 AND ST_YMax(route) <= 90)
        )
        """
    )
    op.execute("CREATE INDEX scenarios_created_at_idx ON scenarios (created_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE scenarios")
    # The postgis extension is left installed: other tables may come to use it.
