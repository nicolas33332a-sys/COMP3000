"""Which reference data is available, read from the provenance manifest.

A scenario can be well-formed but ask for a region or dates that were never
downloaded. Rejecting that when the scenario is created gives the user a
clear message now instead of an empty map or a failed run later.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .scenario import ScenarioInput


@dataclass(frozen=True)
class Coverage:
    west: float
    south: float
    east: float
    north: float
    start_date: date
    end_date: date

    @classmethod
    def from_manifest(cls, path: Path) -> Coverage:
        request = json.loads(path.read_text(encoding="utf-8"))["request"]
        west, south, east, north = request["bbox_west_south_east_north"]
        return cls(
            west,
            south,
            east,
            north,
            date.fromisoformat(request["start_date"]),
            date.fromisoformat(request["end_date"]),
        )

    def problems(self, scenario: ScenarioInput) -> list[dict[str, str]]:
        """Return field/message pairs; an empty list means the scenario is covered."""
        found = []
        r = scenario.region
        if r.west < self.west or r.east > self.east or r.south < self.south or r.north > self.north:
            found.append(
                {
                    "field": "region",
                    "message": "Region must lie inside the available reference data: "
                    f"west {self.west:g}, south {self.south:g}, east {self.east:g}, north {self.north:g}.",
                }
            )
        p = scenario.data_period
        if p.start_date < self.start_date or p.end_date > self.end_date:
            found.append(
                {
                    "field": "data_period",
                    "message": "Data period must lie inside the available reference data: "
                    f"{self.start_date} to {self.end_date}.",
                }
            )
        return found
