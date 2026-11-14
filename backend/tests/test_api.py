from fastapi.testclient import TestClient

from marinescope import __version__
from marinescope.api import app


def test_health_reports_ok_and_version():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}
