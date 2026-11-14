# MarineScope

A full-stack platform for configuring simulated marine surveys, reconstructing sea
surface temperature (SST) from sparse readings, and comparing saved results.
COMP3000 final-year project, BSc Computer Science (Artificial Intelligence).

**Status (14 November 2026): Sprint 1, backlog items MS-02 to MS-06.** What exists and has been run:

- the agreed scenario contract with validation and tests;
- a FastAPI backend that creates, lists and reads scenarios in PostgreSQL/PostGIS and
  serves the downloaded NOAA temperature field;
- a data pipeline that downloads a small NOAA OISST subset, inspects it and plots it;
- a browser app (React, TypeScript, MapLibre) with a scenario form, a list of saved
  scenarios, and a map showing the route over the NOAA reference temperature layer
  with its date, units, source and colour scale.

Not built yet: simulation of vessel readings, reconstruction (IDW or SHRED), accounts,
editing or deleting scenarios.

## Layout

```
backend/     Python package `marinescope`: API, scenario contract, storage, data pipeline,
             database migrations, tests
frontend/    React + TypeScript (Vite) browser app
contracts/   scenario JSON Schema (generated) and the shared example scenario
manifests/   provenance manifest for the downloaded NOAA subset
scripts/     check.ps1 runs every automated check
data/        downloaded NOAA files and subsets (created on demand, ignored by Git)
docker-compose.yml   local PostgreSQL/PostGIS database
```

## Requirements

Versions used when this was written; others may work but were not tried.

- Python 3.12 (3.12.0 used)
- Node.js 24 (24.11.1) with npm 11 (11.6.2)
- Docker Desktop (29.1.3), running, for the database (PostgreSQL 17.5 with PostGIS 3.5.2)
- Windows 11 with PowerShell. Commands below are PowerShell.

## Setup (once)

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[data,dev]"
cd ..\frontend
npm install
cd ..
docker compose up -d --wait
cd backend
.venv\Scripts\python -m alembic upgrade head
cd ..
```

The last commands start the database container and create its tables. Run
`alembic upgrade head` again whenever a new migration appears in `backend/migrations/versions/`.

`backend/requirements.lock.txt` lists the exact Python package versions that were
installed and tested. `frontend/package-lock.json` does the same for npm.

## Start

Start the database if it is not already running (Docker Desktop must be open):

```powershell
docker compose up -d --wait
```

Then two terminals:

```powershell
cd backend
.venv\Scripts\python -m uvicorn marinescope.api:app --reload --port 8000
```

```powershell
cd frontend
npm run dev
```

Open http://localhost:5173. Vite forwards `/api/*` to the backend on port 8000.
The map's temperature layer needs the NOAA pilot data (see "NOAA pilot data" below) to have
been downloaded once on this machine; without it the page says so and the rest still works.
The coastline outline is fetched from MapLibre's public demo tiles and needs internet
access; the temperature grid, region and route do not. API docs, where the scenario endpoints can be
tried by hand: http://127.0.0.1:8000/docs.

Stop the database with `docker compose stop`. Saved scenarios are kept in a Docker
volume and are still there next time. `docker compose down -v` deletes them.

## Check

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
```

This runs the backend tests (`pytest`), the frontend tests (`npm test`) and the
frontend type-check and build (`npm run build`). The database container must be running; the tests use their own
database (`marinescope_test`), so they never touch saved scenarios. No network or
downloaded data is needed.

## NOAA pilot data

```powershell
cd backend
.venv\Scripts\python -m marinescope.pipeline.fetch_oisst --start 2024-06-01 --end 2024-06-14 --bbox -16 44 -4 52
.venv\Scripts\python -m marinescope.pipeline.inspect_oisst
```

The first command downloads 14 daily global files (about 21 MB in total) from NOAA
NCEI into `data/raw/`, writes a 48 kB regional subset to `data/processed/` and
updates `manifests/oisst-pilot-manifest.json`. The second verifies the subset and
writes an inspection report and reference plot to a local `docs/` folder, which is
not kept in Git.

## AI assistance

The work so far was implemented with Claude Code (an AI coding assistant) working from
the student's sprint plan and backlog. Record this as the university's policy requires.
