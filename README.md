# MarineScope

A full-stack platform for configuring simulated marine surveys, reconstructing sea
surface temperature (SST) from sparse readings, and comparing saved results.
COMP3000 final-year project, BSc Computer Science (Artificial Intelligence).

**Status (14 November 2026): first slice of Sprint 1 only.** What exists and has been run:

- a FastAPI backend with one endpoint (`GET /api/health`);
- the agreed scenario contract with validation and tests;
- a data pipeline that downloads a small NOAA OISST subset, inspects it and plots it;
- a React/TypeScript shell page that reaches the API and shows the example scenario.

Not built yet: saving scenarios, the database, the map, the scenario form, simulation,
reconstruction (IDW or SHRED), accounts. See [the slice record](docs/sprints/S01-slice-1-record.md)
for exactly what was checked and what is open.

## Layout

```
backend/     Python package `marinescope`: API, scenario contract, data pipeline, tests
frontend/    React + TypeScript (Vite) browser app
docs/        contracts, data provenance, decisions, requirements, sprint records, evaluation
scripts/     check.ps1 runs every automated check
data/        downloaded NOAA files and subsets (created on demand, ignored by Git)
```

## Requirements

Versions used when this was written; others may work but were not tried.

- Python 3.12 (3.12.0 used)
- Node.js 24 (24.11.1) with npm 11 (11.6.2)
- Windows 11 with PowerShell. Commands below are PowerShell.

## Setup (once)

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[data,dev]"
cd ..\frontend
npm install
cd ..
```

`backend/requirements.lock.txt` lists the exact Python package versions that were
installed and tested. `frontend/package-lock.json` does the same for npm.

## Start

Two terminals:

```powershell
cd backend
.venv\Scripts\python -m uvicorn marinescope.api:app --reload --port 8000
```

```powershell
cd frontend
npm run dev
```

Open http://localhost:5173. The page should say "API reachable". Vite forwards
`/api/*` to the backend on port 8000. API docs: http://127.0.0.1:8000/docs.

## Check

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
```

This runs the backend tests (`pytest`) and the frontend type-check and build
(`npm run build`). It needs no network and no downloaded data.

## NOAA pilot data

```powershell
cd backend
.venv\Scripts\python -m marinescope.pipeline.fetch_oisst --start 2024-06-01 --end 2024-06-14 --bbox -16 44 -4 52
.venv\Scripts\python -m marinescope.pipeline.inspect_oisst
```

The first command downloads 14 daily global files (about 21 MB in total) from NOAA
NCEI into `data/raw/`, writes a 48 kB regional subset to `data/processed/` and
updates `docs/data/oisst-pilot-manifest.json`. The second verifies the subset and
rewrites `docs/evaluation/s01-oisst-pilot/`. Details: [docs/data/oisst-pilot.md](docs/data/oisst-pilot.md).

## Key documents

- [Scenario contract](docs/contracts/scenario-contract.md) - fields, units, coordinate and time conventions
- [NOAA pilot data](docs/data/oisst-pilot.md) - source, region, findings, limits
- [Decisions](docs/decisions/0001-first-slice-decisions.md) - what was chosen and why
- [Open items for MS-01](docs/requirements/MS-01-open-items.md) - questions only the student/supervisor can answer
- [Slice record](docs/sprints/S01-slice-1-record.md) - checks run, problems, next tasks
- [References](docs/report/references.md)

## AI assistance

The first slice was implemented with Claude Code (an AI coding assistant) working from
the student's sprint plan and backlog. Record this as the university's policy requires.
