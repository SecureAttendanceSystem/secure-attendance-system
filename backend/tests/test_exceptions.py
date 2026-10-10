from fastapi import HTTPException


def test_unknown_route_returns_json_404(client):
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_http_error_preserves_status_and_headers(app, client):
    @app.get("/test/http-error")
    def http_error():
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})

    response = client.get("/test/http-error")
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_validation_error_does_not_echo_input(app, client):
    @app.get("/test/validation")
    def validation(value: int):
        return {"value": value}

    response = client.get("/test/validation", params={"value": "private_input"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "value"]
    assert "private_input" not in response.text
    assert "input" not in response.json()["detail"][0]


def test_unexpected_error_is_safe_logged_and_has_cors(app, client, caplog):
    @app.get("/test/unexpected")
    def unexpected():
        raise RuntimeError("private_password")

    response = client.get("/test/unexpected", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "Unhandled RuntimeError" in caplog.text
    assert "private_password" not in caplog.text
    assert "private_password" not in response.text


def test_unexpected_error_does_not_allow_unapproved_origin(app, client):
    @app.get("/test/unexpected")
    def unexpected():
        raise RuntimeError("private_password")

    response = client.get("/test/unexpected", headers={"Origin": "https://unapproved.example"})
    assert response.status_code == 500
    assert "access-control-allow-origin" not in response.headers


def test_lifecycle_logs_startup(client, caplog):
    assert any(
        record.getMessage() == "Starting Secure Attendance API (test)"
        for record in caplog.get_records("setup")
    )
