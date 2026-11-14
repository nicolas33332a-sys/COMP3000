"""FastAPI application: health check and scenario create/list/read (MS-04).

Run from the backend folder:  uvicorn marinescope.api:app --reload

Error responses all have the same shape so the browser can show them:
    {"error": "<code>", "message": "<sentence>", "problems": [{"field", "message"}]}
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from . import __version__, config, repository
from .coverage import Coverage
from .scenario import Scenario, ScenarioInput

router = APIRouter(prefix="/api")

DB_CONNECT_TIMEOUT_SECONDS = 5


def get_session(request: Request) -> Iterator[Session]:
    """One database session per request, closed when the request ends."""
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def _error(status: int, code: str, message: str, problems: list[dict[str, str]] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "message": message, "problems": problems or []})


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "ok"
    except OperationalError:
        database = "unavailable"
    return {"status": "ok", "version": __version__, "database": database}


@router.post("/scenarios", status_code=201, response_model=Scenario)
def create_scenario(data: ScenarioInput, session: SessionDep):
    problems = Coverage.from_manifest(config.manifest_path()).problems(data)
    if problems:
        return _error(422, "validation_error", "The scenario is outside the available data.", problems)
    return repository.create_scenario(session, data)


@router.get("/scenarios")
def list_scenarios(session: SessionDep, limit: Annotated[int, Query(ge=1, le=500)] = 100) -> list[Scenario]:
    return repository.list_scenarios(session, limit)


@router.get("/scenarios/{scenario_id}")
def read_scenario(scenario_id: uuid.UUID, session: SessionDep) -> Scenario:
    scenario = repository.get_scenario(session, scenario_id)
    if scenario is None:
        raise HTTPException(404, f"No scenario with id {scenario_id}.")
    return scenario


def _invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    problems = []
    for err in exc.errors():
        # ("body", "waypoints", 0, "lat") -> "waypoints.0.lat"
        # A rule about the scenario as a whole has no single field: call it "scenario".
        field = ".".join(str(part) for part in err["loc"] if part != "body") or "scenario"
        problems.append({"field": field, "message": err["msg"].removeprefix("Value error, ")})
    return _error(422, "validation_error", "The request is not valid.", problems)


def _database_down(request: Request, exc: OperationalError) -> JSONResponse:
    return _error(503, "database_unavailable", "The database cannot be reached. Is it running?")


def _rejected_by_database(request: Request, exc: IntegrityError) -> JSONResponse:
    # Should not happen: it means a table constraint is stricter than scenario.py.
    # Answer clearly instead of with a bare 500, and fix the validation gap.
    return _error(422, "validation_error", "The database rejected this scenario; nothing was saved.")


def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
    code = "not_found" if exc.status_code == 404 else "http_error"
    return _error(exc.status_code, code, str(exc.detail))


def create_app(database_url: str | None = None) -> FastAPI:
    app = FastAPI(title="MarineScope API", version=__version__)
    # create_engine does not connect yet; connections open on first use.
    # connect_timeout matters: with the database container stopped, a connection
    # attempt was observed to hang indefinitely instead of failing (see MS-04 record).
    app.state.engine = create_engine(
        database_url or config.database_url(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": DB_CONNECT_TIMEOUT_SECONDS},
    )
    app.add_exception_handler(RequestValidationError, _invalid_request)
    app.add_exception_handler(OperationalError, _database_down)
    app.add_exception_handler(IntegrityError, _rejected_by_database)
    app.add_exception_handler(HTTPException, _http_error)
    app.include_router(router)
    return app


app = create_app()
