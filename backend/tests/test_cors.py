import pytest


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://127.0.0.1:3000"])
def test_approved_origin_receives_cors_headers(client, origin):
    response = client.get("/health", headers={"Origin": origin})
    assert response.headers["access-control-allow-origin"] == origin


def test_unapproved_origin_receives_no_cors_permission(client):
    response = client.get("/health", headers={"Origin": "https://unapproved.example"})
    assert "access-control-allow-origin" not in response.headers


def test_approved_preflight_allows_authorization_header(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_unapproved_preflight_is_rejected(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "https://unapproved.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
