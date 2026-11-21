"""Which browser origins may call the API (backend/main.py CORS settings)."""

import pytest
from fastapi.testclient import TestClient

from backend import main


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.mark.parametrize("origin", [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",  # vite preview
    "http://127.0.0.1:3000",
])
def test_local_frontend_may_call_the_api(client, origin):
    response = client.post("/projects", json={"prompt": "A simple task manager"}, headers={"Origin": origin})

    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in response.headers


@pytest.mark.parametrize("origin", [
    "https://evil.example",
    "http://localhost.evil.example",
    "http://127.0.0.1.evil.example:5173",
    "http://evil.example/?http://localhost:5173",
    "null",
])
def test_other_websites_get_no_cors_permission(client, origin):
    response = client.get("/projects/00000000-0000-4000-8000-000000000000", headers={"Origin": origin})

    assert "access-control-allow-origin" not in response.headers


def test_preflight_for_the_frontend_requests(client):
    """The frontend sends Content-Type: application/json, so browsers ask first."""
    for method in ("POST", "GET"):
        response = client.options(
            "/projects",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200, method
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
        assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_preflight_from_another_website_is_refused(client):
    response = client.options(
        "/projects",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_requests_without_an_origin_still_work(client):
    """curl, tests and same-origin navigation (preview, download) send no Origin."""
    assert client.post("/projects", json={"prompt": "A simple task manager"}).status_code == 201
