"""FastAPI application.

First slice: a health endpoint only, so the start command and the frontend
proxy can be verified. Scenario create/list/read arrive with MS-04.

Run from the backend folder:  uvicorn marinescope.api:app --reload
"""

from fastapi import FastAPI

from . import __version__

app = FastAPI(title="MarineScope API", version=__version__)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
