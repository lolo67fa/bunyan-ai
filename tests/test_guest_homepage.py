"""Regression: in guest mode the public site must load even when an address has used up its
new-guest budget (a club on one Wi-Fi, or many cookieless requests), and errors a person
sees in the browser are a readable Arabic page in UTF-8, never raw JSON."""

import pytest
from fastapi.testclient import TestClient

from backend import main, security

SECRET = "test-session-secret-0123456789-abcdefghijklmnop"
HTML = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
IDEA = "I want a web app to manage my tasks with title, due date, priority and status."


@pytest.fixture
def guest_site(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text('<!doctype html><html lang="ar" dir="rtl"><title>بُنيان</title>', encoding="utf-8")
    monkeypatch.setenv("BUNYAN_AUTH", "guest")
    monkeypatch.setenv("BUNYAN_SESSION_SECRET", SECRET)
    monkeypatch.setenv("BUNYAN_COOKIE_SECURE", "false")
    monkeypatch.setenv("BUNYAN_MAX_NEW_SESSIONS_PER_IP_PER_HOUR", "2")
    for reset in (security.guest_sessions.reset, security.limits.reset):
        reset()
    app_routes = list(main.app.router.routes)
    from fastapi.staticfiles import StaticFiles
    main.app.mount("/", StaticFiles(directory=tmp_path, html=True), name="test-frontend")
    yield
    main.app.router.routes[:] = app_routes
    for reset in (security.guest_sessions.reset, security.limits.reset):
        reset()


def use_up_the_budget():
    """New cookieless visitors from this address until no new guest is handed out."""
    for _ in range(3):
        TestClient(main.app).get("/", headers=HTML)
    assert "set-cookie" not in TestClient(main.app).get("/", headers=HTML).headers


def test_homepage_loads_after_the_address_used_its_new_guest_budget(guest_site):
    use_up_the_budget()
    response = TestClient(main.app).get("/", headers=HTML)  # Safari, no cookie, same Wi-Fi
    assert response.status_code == 200 and "بُنيان" in response.text
    assert response.headers["content-type"].startswith("text/html")
    assert "set-cookie" not in response.headers  # no new identity was handed out


def test_existing_guests_on_the_same_network_keep_working(guest_site):
    browser = TestClient(main.app)
    browser.get("/", headers=HTML)
    use_up_the_budget()
    created = browser.post("/projects", json={"prompt": IDEA})
    assert created.status_code == 201  # their cookie is valid: no new session needed


def test_the_api_still_refuses_new_guests_over_the_budget_in_utf8(guest_site):
    use_up_the_budget()
    response = TestClient(main.app).post("/projects", json={"prompt": IDEA})
    assert response.status_code == 429
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    assert "جلسات جديدة كثيرة" in response.json()["detail"]


def test_an_error_opened_in_the_browser_is_an_arabic_page(guest_site):
    use_up_the_budget()
    response = TestClient(main.app).get("/projects/11111111-1111-1111-1111-111111111111/preview/", headers=HTML)
    assert response.status_code == 429
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    body = response.text
    assert body.startswith("<!doctype html>") and 'dir="rtl"' in body and "جلسات جديدة كثيرة" in body
    assert '"detail"' not in body and 'href="/"' in body


def test_not_found_in_the_browser_is_a_page_and_json_for_the_app(guest_site):
    browser = TestClient(main.app)
    pid = "11111111-1111-1111-1111-111111111111"
    page = browser.get(f"/projects/{pid}/preview/", headers=HTML)
    assert page.status_code == 404 and page.headers["content-type"] == "text/html; charset=utf-8"
    api = browser.get(f"/projects/{pid}")
    assert api.status_code == 404 and api.headers["content-type"] == "application/json; charset=utf-8"


def test_cross_site_writes_are_still_refused(guest_site):
    browser = TestClient(main.app)
    browser.get("/", headers=HTML)
    response = browser.post("/projects", json={"prompt": IDEA}, headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
