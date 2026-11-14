"""Write the scenario JSON Schema to contracts/scenario.schema.json.

Run from the backend folder:  python -m marinescope.export_schema
A test fails if the committed file is out of date with scenario.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from .scenario import ScenarioInput

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts" / "scenario.schema.json"


def render_schema() -> str:
    return json.dumps(ScenarioInput.model_json_schema(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(render_schema(), encoding="utf-8", newline="\n")
    print(f"Wrote {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
