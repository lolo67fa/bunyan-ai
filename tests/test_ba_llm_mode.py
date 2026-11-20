"""The API with the Business Analyst in LLM mode (BA_MODE=llm), fully offline.

A fake model answers through the agent's real pipeline (parse, schema, scope guard),
and one test goes through the real direct Anthropic backend with a fake SDK client.
Nothing here needs a key, reaches the network or costs money.
"""

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import main, storage
from backend.agents.business_analyst import analyst, config

REAL_GENERATOR = analyst._default_llm_generator  # captured before the autouse guard replaces it
SAMPLES = Path(__file__).resolve().parents[1] / "backend" / "agents" / "business_analyst" / "samples" / "outputs"
SECRET = "sk-ant-offline-test-value-never-sent"

TASK_IDEA = "I want a web app to manage my tasks with title, due date, priority and status."
INVENTORY_IDEA = "أبغى موقع لإدارة المخزون أقدر أضيف فيه المنتجات وأعدل كمياتها وأسعارها وأحذف المنتجات."


def sample(name):
    return json.loads((SAMPLES / f"{name}.requirements.json").read_text(encoding="utf-8"))


def with_phone(doc):
    doc = json.loads(json.dumps(doc))
    doc["entities"][0]["fields"].append(
        {"name": "phone", "label": "Phone number", "type": "phone", "required": False}
    )
    return doc


class FakeLLM:
    """Stands in for the model: returns queued answers (dict, text or an exception to raise)."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.prompts = []
        self.settings = []

    def __call__(self, description, settings):
        self.prompts.append(description)
        self.settings.append(settings)
        answer = self.answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)


@pytest.fixture
def llm_mode(monkeypatch):
    monkeypatch.setenv("BA_MODE", "llm")
    monkeypatch.setenv("BA_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("BA_LLM_MODEL", "claude-opus-5-5")
    monkeypatch.setenv("BA_LLM_BACKEND", "direct")
    monkeypatch.setenv("BA_MAX_RETRIES", "0")
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)

    def use(*answers):
        fake = FakeLLM(*answers)
        monkeypatch.setattr(analyst, "_default_llm_generator", fake)
        return fake

    return use


@pytest.fixture
def client():
    return TestClient(main.app)


def create(client, idea=TASK_IDEA):
    response = client.post("/projects", json={"prompt": idea})
    assert response.status_code == 201
    return response.json()


def get(client, project):
    return client.get(f"/projects/{project['project_id']}").json()


# ---------- mode selection ----------

def test_mock_is_the_default_and_answers_within_the_request(client):
    project = create(client, "أبغى تطبيق لإدارة المهام")
    assert project["status"] == "awaiting_approval"
    assert project["analysis"]["mode"] == "mock" and project["analysis"]["outcome"] == "succeeded"


def test_llm_mode_runs_the_configured_model_in_the_background(client, llm_mode):
    fake = llm_mode(sample("task_manager_en"))
    project = create(client)
    # The request returns at once; the frontend polls while the model works.
    assert project["status"] == "analyzing" and project["current_agent"] == "business_analyst"
    assert project["analysis"]["mode"] == "llm"
    for field in ("artifacts", "repair_attempt", "metrics", "error", "created_at", "updated_at"):
        assert field in project  # the response contract is unchanged

    done = get(client, project)
    assert done["status"] == "awaiting_approval" and done["error"] is None
    assert done["requirements"]["source_idea"] == TASK_IDEA and done["requirements"]["language"] == "en"
    assert len(fake.prompts) == 1 and TASK_IDEA in fake.prompts[0]
    assert fake.settings[0].mode == "llm" and fake.settings[0].model == "claude-opus-5-5"


def test_llm_mode_goes_through_the_real_direct_backend(client, llm_mode, monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    created, requests = [], []

    class FakeAnthropic:
        def __init__(self, **options):
            created.append(options)
            self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

        def _stream(self, **request):
            requests.append(request)
            message = SimpleNamespace(stop_reason="end_turn", stop_details=None, _request_id="req_fake",
                                      content=[SimpleNamespace(type="text", text=json.dumps(sample("task_manager_en")))])
            return _Stream(message)

    monkeypatch.setattr(analyst, "_default_llm_generator", REAL_GENERATOR)
    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    monkeypatch.setenv("BA_REQUEST_TIMEOUT", "120")
    project = create(client)
    assert get(client, project)["status"] == "awaiting_approval"
    assert created == [{"timeout": 120.0}] and len(requests) == 1
    body = json.dumps(requests[0], ensure_ascii=False)
    assert "claude-opus-5-5" in body and TASK_IDEA in body


class _Stream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return SimpleNamespace(get_final_message=lambda: self.message)

    def __exit__(self, *exc):
        return False


def test_an_invalid_mode_stops_the_server_at_startup(monkeypatch):
    monkeypatch.setenv("BA_MODE", "real")
    with pytest.raises(config.ConfigError, match="BA_MODE"):
        with TestClient(main.app):
            pass


def test_startup_logs_the_mode_without_the_key(monkeypatch, caplog, llm_mode):
    llm_mode()
    with caplog.at_level(logging.INFO):
        with TestClient(main.app):
            pass
    assert "LLM mode (provider anthropic, model claude-opus-5-5, backend direct)" in caplog.text
    assert SECRET not in caplog.text


# ---------- errors: safe, stored, never a silent mock ----------

def test_missing_key_fails_with_a_clear_error_and_no_mock(client, llm_mode, monkeypatch):
    fake = llm_mode()
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    project = get(client, create(client))
    assert project["status"] == "failed" and project["requirements"] is None
    assert project["error"]["code"] == "ba_not_configured" and project["error"]["retryable"] is False
    assert fake.prompts == []  # nothing was sent, and nothing fell back to the mock analyst


def test_auth_failure_is_reported_without_the_key(client, llm_mode, caplog):
    anthropic = pytest.importorskip("anthropic")
    import httpx

    response = httpx.Response(401, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    llm_mode(anthropic.AuthenticationError("invalid x-api-key", response=response, body=None))
    with caplog.at_level(logging.WARNING):
        project = get(client, create(client))
    assert project["status"] == "failed" and project["error"]["code"] == "llm_auth_failed"
    stored = json.dumps(project, ensure_ascii=False)
    assert SECRET not in stored and SECRET not in caplog.text


def test_invalid_model_output_is_a_safe_error(client, llm_mode):
    llm_mode("Sure! Here is the requirements document you asked for.")
    project = get(client, create(client))
    assert project["status"] == "failed" and project["error"]["code"] == "ba_invalid_output"
    assert "Sure!" not in json.dumps(project["error"], ensure_ascii=False)


def test_out_of_scope_requirements_from_the_model_are_rejected(client, llm_mode):
    doc = sample("task_manager_en")
    doc["functional_requirements"][0]["description"] = "Users log in with a password before managing tasks."
    llm_mode(doc)
    project = get(client, create(client))
    assert project["status"] == "failed" and project["error"]["code"] == "ba_invalid_output"


def test_an_out_of_scope_idea_is_rejected(client, llm_mode):
    llm_mode(sample("out_of_scope_ar"))
    project = get(client, create(client, "أبي تطبيق جوال للمتجر مع دفع إلكتروني وتسجيل دخول للعملاء."))
    assert project["status"] == "rejected" and project["requirements"]["status"] == "rejected_out_of_scope"


# ---------- clarification ----------

def test_clarification_answers_reach_the_model_and_are_kept(client, llm_mode):
    fake = llm_mode(sample("vague_idea_en"), sample("vague_idea_en"), sample("task_manager_en"))
    project = get(client, create(client, "I need an app for my stuff"))
    assert project["status"] == "awaiting_clarification"

    first = client.post(f"/projects/{project['project_id']}/answers", json={"answers": {"Q-1": "Tasks"}})
    assert first.status_code == 200 and first.json()["status"] == "analyzing"
    assert get(client, project)["status"] == "awaiting_clarification"

    client.post(f"/projects/{project['project_id']}/answers", json={"answers": {"Q-2": "title and due date"}})
    done = get(client, project)
    assert done["status"] == "awaiting_approval"
    assert done["answers"] == {"Q-1": "Tasks", "Q-2": "title and due date"}  # earlier answers are kept
    assert "- Q-1: Tasks" in fake.prompts[2] and "- Q-2: title and due date" in fake.prompts[2]


# ---------- request changes ----------

def test_feedback_revises_the_reviewed_version(client, llm_mode):
    original = sample("task_manager_en")
    fake = llm_mode(original, with_phone(original))
    project = get(client, create(client))

    response = client.post(f"/projects/{project['project_id']}/approve",
                           json={"approved": False, "feedback": "Add a phone number field"})
    assert response.status_code == 200 and response.json()["status"] == "analyzing"

    revised = get(client, project)
    assert revised["status"] == "awaiting_approval"
    assert "phone" in [f["name"] for f in revised["requirements"]["entities"][0]["fields"]]
    assert revised["revision"]["changed"] is True and revised["revision"]["mode"] == "llm"
    assert revised["revision"]["added_fields"] == [{"entity": "Task", "field": "phone", "label": "Phone number"}]
    assert revised["revision"]["feedback"] == "Add a phone number field"
    # The model saw the version the user reviewed, and the feedback.
    assert "CURRENT requirements.json" in fake.prompts[1] and "Add a phone number field" in fake.prompts[1]
    assert revised["feedback_history"][0]["feedback"] == "Add a phone number field"

    approved = client.post(f"/projects/{project['project_id']}/approve", json={"approved": True})
    assert approved.status_code == 200 and approved.json()["status"] == "designing"


def test_feedback_that_changes_nothing_is_reported_as_unchanged(client, llm_mode):
    original = sample("task_manager_en")
    llm_mode(original, original)
    project = get(client, create(client))
    client.post(f"/projects/{project['project_id']}/approve", json={"approved": False, "feedback": "Add a phone field"})
    revised = get(client, project)
    assert revised["revision"]["changed"] is False and revised["revision"]["added_fields"] == []


def test_mock_mode_revision_is_honest_too(client):
    project = create(client, TASK_IDEA)
    client.post(f"/projects/{project['project_id']}/approve", json={"approved": False, "feedback": "Add a phone field"})
    revised = get(client, project)
    assert revised["revision"]["mode"] == "mock" and revised["revision"]["changed"] is False


def test_failed_revision_keeps_the_reviewed_version(client, llm_mode):
    anthropic = pytest.importorskip("anthropic")
    import httpx

    response = httpx.Response(429, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    original = sample("task_manager_en")
    llm_mode(original, anthropic.RateLimitError("rate limited", response=response, body=None))
    project = get(client, create(client))
    client.post(f"/projects/{project['project_id']}/approve", json={"approved": False, "feedback": "Add a phone field"})

    after = get(client, project)
    assert after["status"] == "awaiting_approval"  # back to review, nothing lost
    assert after["requirements"] == project["requirements"]
    assert after["error"]["code"] == "llm_rate_limited" and after["error"]["retryable"] is True
    assert "revision" not in after


# ---------- Architect compatibility ----------

def test_arabic_llm_requirements_build_through_the_whole_pipeline(client, llm_mode):
    llm_mode(sample("inventory_dialect_ar"))
    project = get(client, create(client, INVENTORY_IDEA))
    assert project["status"] == "awaiting_approval" and project["requirements"]["language"] == "ar"
    assert project["compatibility"] == {"supported": True, "message": None, "reasons": []}

    client.post(f"/projects/{project['project_id']}/approve", json={"approved": True})
    done = get(client, project)
    assert done["status"] == "completed"  # Architect, Developer and PM ran (QA is off in tests)
    names = {a["name"] for a in done["artifacts"] if a["available"]}
    assert {"architecture.json", "index.html", "app.js", "project_plan.md"} <= names


def test_multi_entity_requirements_are_flagged_before_approval(client, llm_mode):
    llm_mode(sample("inventory_manager_ar"))
    project = get(client, create(client, "أبي نظام مخزون فيه تصنيفات ومنتجات وكل منتج تابع لتصنيف"))
    assert project["status"] == "awaiting_approval"
    assert project["compatibility"]["supported"] is False and project["compatibility"]["message"]
    assert any("exactly one entity" in r for r in project["compatibility"]["reasons"])
    # Approval still behaves as before: the run stops at the Architect with a clear error.
    client.post(f"/projects/{project['project_id']}/approve", json={"approved": True})
    assert get(client, project)["error"]["code"] == "architecture_unsupported"


def test_an_architect_crash_is_flagged_instead_of_hidden(client, llm_mode, monkeypatch):
    def crash(requirements):
        raise ValueError("verbatim message AC-17 is not used")

    monkeypatch.setattr(main, "build_architecture", crash)
    llm_mode(sample("task_manager_en"))
    project = get(client, create(client))
    assert project["status"] == "awaiting_approval"
    assert project["compatibility"]["supported"] is False and project["compatibility"]["message"]
    assert project["compatibility"]["reasons"] == ["architect_check_failed: ValueError"]


# ---------- restart during an analysis ----------

def test_interrupted_analysis_is_recovered_on_startup():
    first = {"project_id": "11111111-1111-1111-1111-111111111111", "status": "analyzing", "requirements": None,
             "analysis": {"kind": "initial", "previous_status": None}}
    revision = {"project_id": "22222222-2222-2222-2222-222222222222", "status": "analyzing",
                "requirements": sample("task_manager_en"),
                "analysis": {"kind": "feedback", "previous_status": "awaiting_approval"}}
    for p in (first, revision):
        storage.save_project(p)
    main.recover_interrupted_projects()
    assert storage.load_project(first["project_id"])["status"] == "failed"
    restored = storage.load_project(revision["project_id"])
    assert restored["status"] == "awaiting_approval" and restored["error"]["code"] == "analysis_interrupted"
