"""Guest mode (BUNYAN_AUTH=guest): no login, but every visitor is a separate, limited owner."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from backend import main, security, storage

IDEA = "I want a web app to manage my tasks with title, due date, priority and status."
SECRET = "test-session-secret-0123456789-abcdefghijklmnop"


@pytest.fixture
def guest_mode(monkeypatch):
    monkeypatch.setenv("BUNYAN_AUTH", "guest")
    monkeypatch.setenv("BUNYAN_SESSION_SECRET", SECRET)
    monkeypatch.setenv("BUNYAN_COOKIE_SECURE", "false")  # the test client talks plain http
    monkeypatch.setenv("BUNYAN_MAX_PROJECTS_PER_USER_PER_DAY", "3")
    for reset in (security.guest_sessions.reset, security.limits.reset, security.authenticator.reset):
        reset()
    yield
    for reset in (security.guest_sessions.reset, security.limits.reset, security.authenticator.reset):
        reset()


def guest():
    """A new browser: its own cookie jar, so its own guest identity."""
    return TestClient(main.app)


def create(client, idea=IDEA):
    response = client.post("/projects", json={"prompt": idea})
    assert response.status_code == 201, response.text
    return response.json()


# ---------- the session ----------

def test_first_visit_gets_a_secure_guest_cookie_and_no_login(guest_mode, monkeypatch):
    monkeypatch.setenv("BUNYAN_COOKIE_SECURE", "true")
    response = guest().get("/")  # no login prompt: no 401, no WWW-Authenticate
    assert response.status_code != 401 and "WWW-Authenticate" not in response.headers
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{security.GUEST_COOKIE}=")
    for attribute in ("HttpOnly", "Secure", "SameSite=lax", "Path=/", f"Max-Age={security.GUEST_SESSION_SECONDS}"):
        assert attribute.lower() in cookie.lower(), attribute


def test_health_sets_no_cookie(guest_mode):
    response = guest().get("/health")
    assert response.status_code == 200 and "set-cookie" not in response.headers


def test_reload_keeps_the_same_guest(guest_mode):
    browser = guest()
    project = create(browser)
    assert project["owner"].startswith("guest:")
    again = browser.get(f"/projects/{project['project_id']}")  # the cookie came back
    assert again.status_code == 200 and "set-cookie" not in again.headers
    assert create(browser)["owner"] == project["owner"]


def test_session_ids_are_random_and_signed(guest_mode):
    users = {security.issue_guest_cookie()[0] for _ in range(50)}
    assert len(users) == 50
    user, cookie = security.issue_guest_cookie()
    assert security.read_guest_cookie(cookie) == user
    sid, issued, mac = cookie.split(".")
    assert security.read_guest_cookie(f"{sid}x.{issued}.{mac}") is None   # another id, same signature
    assert security.read_guest_cookie(f"{sid}.{issued}.{'0' * 64}") is None  # forged signature
    assert security.read_guest_cookie("guest:alice") is None


def test_expired_cookies_are_refused(guest_mode):
    user, cookie = security.issue_guest_cookie(now=time.time() - security.GUEST_SESSION_SECONDS - 10)
    assert security.read_guest_cookie(cookie) is None


def test_a_forged_cookie_cannot_take_over_a_project(guest_mode):
    victim = guest()
    pid = create(victim)["project_id"]
    attacker = guest()
    sid = create(victim)["owner"].split(":", 1)[1]
    attacker.cookies.set(security.GUEST_COOKIE, f"{sid}.{int(time.time())}.{'a' * 64}")
    response = attacker.get(f"/projects/{pid}")
    assert response.status_code == 404  # the bad cookie is replaced by a fresh guest, who owns nothing


# ---------- isolation between guests ----------

def test_guests_cannot_reach_each_others_projects(guest_mode):
    alice, bob = guest(), guest()
    a = create(alice)
    b = create(bob)
    assert a["owner"] != b["owner"]  # never one shared account
    pid = a["project_id"]
    alice.post(f"/projects/{pid}/approve", json={"approved": True})
    assert alice.get(f"/projects/{pid}").json()["status"] == "completed"
    for path in [f"/projects/{pid}", f"/projects/{pid}/artifacts/requirements.json", f"/projects/{pid}/preview",
                 f"/projects/{pid}/preview/", f"/projects/{pid}/preview/app.js", f"/projects/{pid}/download"]:
        assert alice.get(path, follow_redirects=False).status_code in (200, 307), path
        assert bob.get(path, follow_redirects=False).status_code == 404, path
    assert bob.post(f"/projects/{pid}/approve", json={"approved": False, "feedback": "Add a field"}).status_code == 404
    assert bob.get(f"/projects/{b['project_id']}").status_code == 200


def test_projects_from_the_login_mode_stay_private(guest_mode):
    storage.save_project({"project_id": "11111111-1111-1111-1111-111111111111", "owner": "tester01", "status": "completed"})
    assert guest().get("/projects/11111111-1111-1111-1111-111111111111").status_code == 404
    assert storage.load_project("11111111-1111-1111-1111-111111111111")["owner"] == "tester01"  # intact


# ---------- limits ----------

def test_three_projects_per_guest_per_day(guest_mode):
    browser = guest()
    for _ in range(3):
        create(browser)
    response = browser.post("/projects", json={"prompt": IDEA})
    assert response.status_code == 429 and "(3)" in response.json()["detail"]


def test_new_cookies_do_not_bypass_the_address_limit(guest_mode, monkeypatch):
    monkeypatch.setenv("BUNYAN_MAX_PROJECTS_PER_IP_PER_DAY", "4")
    first = guest()
    for _ in range(3):
        create(first)
    second = guest()  # "cleared cookies": a new guest from the same address
    create(second)
    assert second.post("/projects", json={"prompt": IDEA}).status_code == 429


def test_site_wide_daily_project_cap(guest_mode, monkeypatch):
    monkeypatch.setenv("BUNYAN_MAX_PROJECTS_PER_DAY", "2")
    create(guest())
    create(guest())
    assert guest().post("/projects", json={"prompt": IDEA}).status_code == 429


def test_new_guest_identities_are_limited_per_address(guest_mode, monkeypatch):
    monkeypatch.setenv("BUNYAN_MAX_NEW_SESSIONS_PER_IP_PER_HOUR", "3")
    for _ in range(3):
        assert "set-cookie" in guest().get("/").headers  # each new browser gets its guest cookie
    response = guest().get("/")
    assert response.status_code == 429 and "set-cookie" not in response.headers


def test_request_rate_per_address(guest_mode, monkeypatch):
    monkeypatch.setenv("BUNYAN_MAX_REQUESTS_PER_MINUTE_PER_IP", "2")
    create(guest())
    create(guest())
    assert guest().post("/projects", json={"prompt": IDEA}).status_code == 429


def test_daily_counters_are_stored(guest_mode):
    browser = guest()
    owner = create(browser)["owner"]
    usage = json.loads((storage.DATA_DIR / "usage.json").read_text())
    assert usage["projects"][owner] == 1 and usage["projects_total"] == 1 and sum(usage["projects_by_ip"].values()) == 1


# ---------- no paid model, no cross-site writes, safe configuration ----------

def test_guest_mode_refuses_the_real_analyst(guest_mode, monkeypatch):
    monkeypatch.setenv("BA_MODE", "llm")
    with pytest.raises(RuntimeError, match="BA_MODE=mock"):
        with TestClient(main.app):
            pass
    monkeypatch.setenv("BA_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("BA_LLM_MODEL", "claude-opus-5-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-offline-test-value-never-sent")
    response = guest().post("/projects", json={"prompt": IDEA})  # even if startup were bypassed
    assert response.status_code == 403


def test_guest_mode_needs_a_strong_secret(monkeypatch):
    monkeypatch.setenv("BUNYAN_AUTH", "guest")
    monkeypatch.setenv("BUNYAN_SESSION_SECRET", "short")
    with pytest.raises(RuntimeError, match="BUNYAN_SESSION_SECRET"):
        with TestClient(main.app):
            pass


def test_cross_site_writes_are_refused(guest_mode):
    browser = guest()
    browser.get("/")
    response = browser.post("/projects", json={"prompt": IDEA}, headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert browser.post("/projects", json={"prompt": IDEA}, headers={"Origin": "http://testserver"}).status_code == 201


def test_the_login_mode_still_works_as_a_rollback(monkeypatch):
    monkeypatch.setenv("BUNYAN_AUTH", "required")
    monkeypatch.setenv("BUNYAN_USERS", f"alice:{security.hash_password('alice-password-1', 1000)}")
    security.authenticator.reset()
    response = TestClient(main.app).get("/")
    assert response.status_code == 401 and "set-cookie" not in response.headers
