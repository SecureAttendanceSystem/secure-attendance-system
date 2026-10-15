from unittest.mock import MagicMock

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from app.database.connection import get_database_engine


def test_health_does_not_require_database(app, client):
    def unavailable_engine():
        raise AssertionError("Liveness must not depend on database access")

    app.dependency_overrides[get_database_engine] = unavailable_engine
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_executes_connectivity_query(app, client):
    engine = MagicMock(spec=Engine)
    app.dependency_overrides[get_database_engine] = lambda: engine
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    connection = engine.connect.return_value.__enter__.return_value
    assert str(connection.execute.call_args.args[0]) == "SELECT 1"


def test_database_failure_returns_503_without_credentials(app, client, caplog):
    engine = MagicMock(spec=Engine)
    engine.connect.side_effect = OperationalError(None, None, Exception("private_password"))
    app.dependency_overrides[get_database_engine] = lambda: engine
    response = client.get("/health/db")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
    assert "private_password" not in response.text
    assert "private_password" not in caplog.text
    assert "Database health check failed" in caplog.text


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_documentation_is_accessible(client, path):
    assert client.get(path).status_code == 200


def test_openapi_includes_modular_health_routes(client):
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "Secure Attendance API"
    assert schema["paths"]["/health"]["get"]["tags"] == ["Health"]
    assert "/health/db" in schema["paths"]
