"""Access control and limits for the shared club deployment (BUNYAN_AUTH=required)."""

import base64
import json

import pytest
from fastapi.testclient import TestClient

from backend import main, security, storage

IDEA = "I want a web app to manage my tasks with title, due date, priority and status."


def basic(name, password):
    return {"Authorization": "Basic " + base64.b64encode(f"{name}:{password}".encode()).decode()}


ALICE = basic("alice", "alice-password-1")
BOB = basic("bob", "bob-password-22")


@pytest.fixture
def secured(monkeypatch):
    users = [f"alice:{security.hash_password('alice-password-1', 1000)}",
             f"bob:{security.hash_password('bob-password-22', 1000)}"]
    monkeypatch.setenv("BUNYAN_AUTH", "required")
    monkeypatch.setenv("BUNYAN_USERS", ",".join(users))
    security.authenticator.reset()
    security.limits.reset()
    yield TestClient(main.app)
    security.authenticator.reset()
    security.limits.reset()


def create(client, headers, idea=IDEA):
    response = client.post("/projects", json={"prompt": idea}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# ---------- authentication ----------

def test_every_route_needs_credentials_except_health(secured):
    assert secured.get("/health").status_code == 200
    for method, path in [("get", "/projects/11111111-1111-1111-1111-111111111111"), ("post", "/projects"),
                         ("get", "/projects/11111111-1111-1111-1111-111111111111/download"), ("get", "/")]:
        response = getattr(secured, method)(path)
        assert response.status_code == 401, path
        assert response.headers["WWW-Authenticate"].startswith("Basic ")


def test_wrong_password_and_unknown_user_are_refused(secured):
    assert secured.post("/projects", json={"prompt": IDEA}, headers=basic("alice", "wrong")).status_code == 401
    assert secured.post("/projects", json={"prompt": IDEA}, headers=basic("mallory", "x")).status_code == 401
    assert secured.post("/projects", json={"prompt": IDEA}, headers={"Authorization": "Basic !!!"}).status_code == 401


def test_repeated_failures_are_blocked(secured):
    for _ in range(security.Authenticator.MAX_FAILURES):
        secured.get("/projects/x", headers=basic("alice", "guess"))
    response = secured.get("/health")
    assert response.status_code == 200  # the health check stays open
    assert secured.post("/projects", json={"prompt": IDEA}, headers=ALICE).status_code == 429


def test_cors_is_not_authentication(secured):
    response = secured.post("/projects", json={"prompt": IDEA}, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 401


def test_the_server_refuses_to_start_without_users(monkeypatch):
    monkeypatch.setenv("BUNYAN_AUTH", "required")
    monkeypatch.delenv("BUNYAN_USERS", raising=False)
    with pytest.raises(RuntimeError, match="BUNYAN_USERS is empty"):
        with TestClient(main.app):
            pass


def test_malformed_users_and_auth_values_are_errors(monkeypatch):
    monkeypatch.setenv("BUNYAN_USERS", "alice:plaintext-password")
    with pytest.raises(RuntimeError, match="malformed"):
        security.load_users()
    monkeypatch.setenv("BUNYAN_AUTH", "maybe")
    with pytest.raises(RuntimeError, match="BUNYAN_AUTH"):
        security.auth_required()


def test_password_hashes_have_no_dollar_signs_and_verify():
    stored = security.hash_password("a long password", 1000)
    assert "$" not in stored and stored.startswith("pbkdf2:1000:")
    assert security._check_password("a long password", stored)
    assert not security._check_password("another password", stored)


# ---------- one tester cannot reach another tester's projects ----------

def test_projects_belong_to_their_owner_on_every_route(secured):
    project = create(secured, ALICE)
    pid = project["project_id"]
    assert project["owner"] == "alice"
    secured.post(f"/projects/{pid}/approve", json={"approved": True}, headers=ALICE)
    assert secured.get(f"/projects/{pid}", headers=ALICE).json()["status"] == "completed"

    for path in [f"/projects/{pid}", f"/projects/{pid}/artifacts/requirements.json", f"/projects/{pid}/preview",
                 f"/projects/{pid}/preview/", f"/projects/{pid}/preview/app.js", f"/projects/{pid}/download"]:
        assert secured.get(path, headers=ALICE, follow_redirects=False).status_code in (200, 307), path
        assert secured.get(path, headers=BOB, follow_redirects=False).status_code == 404, path
    assert secured.post(f"/projects/{pid}/approve", json={"approved": False, "feedback": "Add a field"},
                        headers=BOB).status_code == 404
    assert secured.post(f"/projects/{pid}/answers", json={"answers": {"Q-1": "x"}}, headers=BOB).status_code == 404


# ---------- limits ----------

def test_daily_project_limit_per_user(secured, monkeypatch):
    monkeypatch.setenv("BUNYAN_MAX_PROJECTS_PER_USER_PER_DAY", "2")
    create(secured, ALICE)
    create(secured, ALICE)
    response = secured.post("/projects", json={"prompt": IDEA}, headers=ALICE)
    assert response.status_code == 429 and "الحد اليومي" in response.json()["detail"]
    create(secured, BOB)  # other users keep their own quota


def test_daily_analysis_limit_counts_change_requests(secured, monkeypatch):
    monkeypatch.setenv("BUNYAN_MAX_ANALYSES_PER_USER_PER_DAY", "2")
    pid = create(secured, ALICE)["project_id"]
    ok = secured.post(f"/projects/{pid}/approve", json={"approved": False, "feedback": "Add a notes field"}, headers=ALICE)
    assert ok.status_code == 200
    blocked = secured.post(f"/projects/{pid}/approve", json={"approved": False, "feedback": "Add a phone field"}, headers=ALICE)
    assert blocked.status_code == 429


def test_request_rate_limit(secured, monkeypatch):
    monkeypatch.setenv("BUNYAN_MAX_REQUESTS_PER_MINUTE", "3")
    for _ in range(3):
        create(secured, ALICE)
    assert secured.post("/projects", json={"prompt": IDEA}, headers=ALICE).status_code == 429


def test_llm_daily_cap_and_concurrency(secured, monkeypatch):
    monkeypatch.setenv("BUNYAN_MAX_LLM_ANALYSES_PER_DAY", "2")
    monkeypatch.setenv("BUNYAN_MAX_CONCURRENT_ANALYSES", "1")
    security.limits.reserve("alice", new_project=True, llm=True)
    with pytest.raises(Exception) as busy:
        security.limits.reserve("bob", new_project=True, llm=True)
    assert busy.value.status_code == 429 and "مشغول" in busy.value.detail
    security.limits.release()
    security.limits.reserve("bob", new_project=True, llm=True)
    security.limits.release()
    with pytest.raises(Exception) as cap:
        security.limits.reserve("alice", new_project=False, llm=True)
    assert cap.value.status_code == 429 and "حصة" in cap.value.detail


def test_daily_counters_survive_a_restart(secured):
    create(secured, ALICE)
    usage = json.loads((storage.DATA_DIR / "usage.json").read_text())
    assert usage["projects"] == {"alice": 1} and usage["analyses"] == {"alice": 1}


# ---------- isolation of generated code ----------

def test_preview_is_served_in_an_opaque_sandbox(secured):
    pid = create(secured, ALICE)["project_id"]
    secured.post(f"/projects/{pid}/approve", json={"approved": True}, headers=ALICE)
    csp = secured.get(f"/projects/{pid}/preview/", headers=ALICE).headers["Content-Security-Policy"]
    assert csp.startswith("sandbox allow-scripts allow-forms") and "allow-same-origin" not in csp
    assert "default-src 'none'" in csp  # no requests to the API or anywhere else


def test_qa_runs_generated_code_without_secrets(tmp_path, monkeypatch):
    from backend.agents.qa_tester import runner

    (tmp_path / "index.html").write_text("<!doctype html>")
    (tmp_path / "requirements.json").write_text("{}")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-offline-test-value-never-sent")
    monkeypatch.setenv("BUNYAN_USERS", "alice:pbkdf2:1:00:00")
    seen = {}

    def fake_run(cmd, cwd, env, **kwargs):
        seen.update(env)
        raise RuntimeError("stop before Playwright")

    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/bin/npx")
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="stop before Playwright"):
        runner.run_qa(tmp_path, tmp_path / "requirements.json")
    assert "ANTHROPIC_API_KEY" not in seen and "BUNYAN_USERS" not in seen and seen["APP_DIR"]


def test_qa_server_port_never_collides_with_the_web_server(tmp_path, monkeypatch):
    from backend.agents.qa_tester import runner

    (tmp_path / "index.html").write_text("<!doctype html>")
    (tmp_path / "requirements.json").write_text("{}")
    monkeypatch.setenv("PORT", "8000")  # what Docker and Railway set for uvicorn
    seen = {}

    def fake_run(cmd, cwd, env, **kwargs):
        seen.update(env)
        raise RuntimeError("stop")

    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/bin/npx")
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        runner.run_qa(tmp_path, tmp_path / "requirements.json")
    assert seen["PORT"] == "4317"
