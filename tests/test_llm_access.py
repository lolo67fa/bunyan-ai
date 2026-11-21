"""Protected real Business Analyst on the public guest site (BUNYAN_LLM_ACCESS=codes).

No network and no cost: the Anthropic client is a stand-in that answers with the unedited
output of the real paid run 44769184001 and reports that run's real token usage. The request
still goes through the production path (analyze -> direct_llm.run_direct -> usage hook).
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import llm_access, llm_budget, main, security, storage
from backend.agents.business_analyst import analyst
from backend.agents.business_analyst.direct_llm import run_direct

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "backend/agents/architect/tests/fixtures/real_llm_library_ar.requirements.json"
IDEA = ("أبغى تطبيق لإدارة مكتبة شخصية، أقدر أضيف الكتب بعنوانها واسم المؤلف والتصنيف وتاريخ القراءة والتقييم، "
        "وأعدل البيانات وأحذف الكتب وأبحث حسب العنوان أو المؤلف.")
MOCK_IDEA = "I want a web app to manage my tasks with title, due date, priority and status."
CODE = "club-demo-code-2026"
SECRET = "test-session-secret-0123456789-abcdefghijklmnop"


class StandInAnthropic:
    """client.beta.messages.stream(...) like the SDK; counts every request it would have sent."""

    def __init__(self):
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **request):
        self.requests.append(request)
        message = SimpleNamespace(stop_reason="end_turn", stop_details=None, _request_id="req_offline",
                                  model="claude-opus-5-5",
                                  usage=SimpleNamespace(input_tokens=6164, output_tokens=12429),  # run 44769184001
                                  content=[SimpleNamespace(type="text", text=REAL.read_text(encoding="utf-8"))])
        return _Ctx(message)


class _Ctx:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return SimpleNamespace(get_final_message=lambda: self.message)

    def __exit__(self, *exc):
        return False


@pytest.fixture
def site(monkeypatch):
    env = {
        "BUNYAN_AUTH": "guest", "BUNYAN_SESSION_SECRET": SECRET, "BUNYAN_COOKIE_SECURE": "false",
        "BA_MODE": "mock",  # the public default stays mock
        "BUNYAN_LLM_ACCESS": "codes",
        "BUNYAN_LLM_ACCESS_CODES": f"club:{security.hash_password(CODE, 1000)}",
        "BA_LLM_PROVIDER": "anthropic", "BA_LLM_MODEL": "claude-opus-5-5", "BA_LLM_BACKEND": "direct",
        "BA_MAX_RETRIES": "0", "BA_SDK_MAX_RETRIES": "0", "BA_FALLBACKS": "off", "BA_MAX_TOKENS": "32000",
        "ANTHROPIC_API_KEY": "sk-ant-offline-test-value-never-sent",
        "BUNYAN_LLM_DAILY_BUDGET_USD": "2", "BUNYAN_LLM_MAX_PER_CODE_PER_DAY": "3", "BUNYAN_TOTAL_LLM_BUDGET_USD": "5.00", "BUNYAN_LLM_BUDGET_STARTING_SPENT_USD": "0",
        "BUNYAN_MAX_PROJECTS_PER_USER_PER_DAY": "10",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    fake = StandInAnthropic()
    monkeypatch.setattr(analyst, "_default_llm_generator", lambda d, s: run_direct(d, s, client=fake))
    for reset in (security.guest_sessions.reset, security.limits.reset, security.authenticator.reset,
                  llm_access.access.reset):
        reset()
    with TestClient(main.app):  # runs the startup checks
        pass
    yield fake
    for reset in (security.guest_sessions.reset, security.limits.reset, llm_access.access.reset):
        reset()


def browser():
    client = TestClient(main.app)
    client.get("/llm-access")  # gets its guest cookie
    return client


def unlock(client, code=CODE):
    return client.post("/llm-access", json={"code": code})


def spent():
    return json.loads((storage.DATA_DIR / "llm_access.json").read_text(encoding="utf-8"))


def test_without_a_code_guests_get_the_mock_and_no_paid_request(site):
    guest = browser()
    assert guest.get("/llm-access").json() == {"available": True, "enabled": False}
    project = guest.post("/projects", json={"prompt": MOCK_IDEA}).json()
    assert project["analysis"]["mode"] == "mock" and site.requests == []


def test_a_valid_code_unlocks_the_real_analyst_for_that_session_only(site):
    alice, bob = browser(), browser()
    assert unlock(alice).json() == {"available": True, "enabled": True, "remaining_today": 3}
    created = alice.post("/projects", json={"prompt": IDEA})
    assert created.status_code == 200 or created.status_code == 201
    project = alice.get(f"/projects/{created.json()['project_id']}").json()
    assert project["analysis"]["mode"] == "llm" and project["status"] == "awaiting_approval"
    assert project["requirements"]["entities"][0]["name"] == "Book" and project["requirements"]["language"] == "ar"
    assert len(site.requests) == 1 and site.requests[0]["max_tokens"] == 32000
    assert spent()["spent_usd"] == 0.2732  # the real usage, not the worst case
    # bob never entered a code: still the mock, no paid request
    assert bob.post("/projects", json={"prompt": MOCK_IDEA}).json()["analysis"]["mode"] == "mock"
    assert len(site.requests) == 1


def test_revision_uses_the_real_analyst_and_counts(site):
    alice = browser()
    unlock(alice)
    pid = alice.post("/projects", json={"prompt": IDEA}).json()["project_id"]
    r = alice.post(f"/projects/{pid}/approve", json={"approved": False, "feedback": "أضف حقل ملاحظات"})
    assert r.status_code == 200
    assert len(site.requests) == 2 and alice.get("/llm-access").json()["remaining_today"] == 1


def test_the_real_requirements_go_through_the_pipeline(site):
    alice = browser()
    unlock(alice)
    pid = alice.post("/projects", json={"prompt": IDEA}).json()["project_id"]
    alice.post(f"/projects/{pid}/approve", json={"approved": True})
    project = alice.get(f"/projects/{pid}").json()
    assert project["status"] == "completed", project.get("error")
    arch = alice.get(f"/projects/{pid}/artifacts/architecture.json").json()
    assert arch["entity"]["name"] == "Book" and arch["warnings"] == []


def test_wrong_codes_are_refused_and_rate_limited(site):
    guest = browser()
    assert unlock(guest, "not-the-code").status_code == 403
    for _ in range(llm_access.MAX_FAILURES - 1):
        unlock(guest, "still-wrong")
    assert unlock(guest, CODE).status_code == 429  # even the right code waits now
    assert guest.get("/llm-access").json()["enabled"] is False


def test_per_code_daily_cap(site, monkeypatch):
    monkeypatch.setenv("BUNYAN_LLM_MAX_PER_CODE_PER_DAY", "1")
    alice = browser()
    unlock(alice)
    alice.post("/projects", json={"prompt": IDEA})
    second = alice.post("/projects", json={"prompt": IDEA})
    assert second.status_code == 429 and "الحد اليومي" in second.json()["detail"]
    assert len(site.requests) == 1


def test_daily_budget_is_never_exceeded(site, monkeypatch):
    # worst case per request: 20,000 in + 32,000 out on claude-opus-5-5 = 0.72 USD; real cost 0.2732
    monkeypatch.setenv("BUNYAN_LLM_DAILY_BUDGET_USD", "1.0")
    alice = browser()
    unlock(alice)
    assert alice.post("/projects", json={"prompt": IDEA}).status_code in (200, 201)   # 0 + 0.72 <= 1
    assert alice.post("/projects", json={"prompt": IDEA}).status_code in (200, 201)   # 0.27 + 0.72 <= 1
    third = alice.post("/projects", json={"prompt": IDEA})                             # 0.55 + 0.72 > 1
    assert third.status_code == 429 and "ميزانية" in third.json()["detail"]
    assert len(site.requests) == 2 and spent()["spent_usd"] == pytest.approx(0.5464)


def test_cross_site_unlock_is_refused(site):
    guest = browser()
    assert guest.post("/llm-access", json={"code": CODE}, headers={"Origin": "https://evil.example"}).status_code == 403


@pytest.mark.parametrize("change, message", [
    ({"BA_MAX_RETRIES": "1"}, "BA_MAX_RETRIES=0"),
    ({"BA_SDK_MAX_RETRIES": "2"}, "BA_SDK_MAX_RETRIES=0"),
    ({"BA_FALLBACKS": "on"}, "BA_FALLBACKS=off"),
    ({"BA_LLM_BACKEND": "crewai"}, "BA_LLM_BACKEND=direct"),
    ({"BA_MAX_TOKENS": "64000"}, "BA_MAX_TOKENS at most 32000"),
    ({"BUNYAN_LLM_DAILY_BUDGET_USD": "0.5"}, "below the cost of one request"),
    ({"BUNYAN_LLM_ACCESS_CODES": ""}, "BUNYAN_LLM_ACCESS_CODES is empty"),
])
def test_unsafe_configurations_refuse_to_start(site, monkeypatch, change, message):
    for k, v in change.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(RuntimeError, match=message):
        with TestClient(main.app):
            pass


def test_switched_off_by_default(monkeypatch):
    monkeypatch.delenv("BUNYAN_LLM_ACCESS", raising=False)
    assert llm_access.enabled() is False
    assert TestClient(main.app).get("/llm-access").json() == {"available": False, "enabled": False}


def test_guest_mode_still_refuses_a_global_real_analyst(site, monkeypatch):
    monkeypatch.setenv("BA_MODE", "llm")
    with pytest.raises(RuntimeError, match="BA_MODE=mock"):
        with TestClient(main.app):
            pass


def test_clarification_round_with_the_real_analyst(site, monkeypatch):
    """The model asks questions, the tester answers, the model is called again; both calls count."""
    samples = ROOT / "backend/agents/business_analyst/samples/outputs"
    texts = [(samples / "vague_idea_en.requirements.json").read_text(encoding="utf-8"),
             (samples / "task_manager_en.requirements.json").read_text(encoding="utf-8")]
    calls = []

    class Sequenced(StandInAnthropic):
        def _stream(self, **request):
            calls.append(request)
            message = SimpleNamespace(stop_reason="end_turn", stop_details=None, _request_id="req_offline",
                                      model="claude-opus-5-5", usage=SimpleNamespace(input_tokens=6000, output_tokens=9000),
                                      content=[SimpleNamespace(type="text", text=texts[len(calls) - 1])])
            return _Ctx(message)

    fake = Sequenced()
    monkeypatch.setattr(analyst, "_default_llm_generator", lambda d, s: run_direct(d, s, client=fake))
    alice = browser()
    unlock(alice)
    pid = alice.post("/projects", json={"prompt": "I want an app to keep track of my work stuff and things"}).json()["project_id"]
    project = alice.get(f"/projects/{pid}").json()
    assert project["status"] == "awaiting_clarification" and project["analysis"]["mode"] == "llm"
    questions = project["requirements"]["clarification_questions"]
    answers = {q["id"]: (q.get("suggested_default") or "Tasks with title, due date, priority and status") for q in questions}
    assert alice.post(f"/projects/{pid}/answers", json={"answers": answers}).status_code == 200
    project = alice.get(f"/projects/{pid}").json()
    assert project["status"] == "awaiting_approval" and len(calls) == 2
    assert alice.get("/llm-access").json()["remaining_today"] == 1  # both analyses counted on the code
    assert spent()["spent_usd"] == pytest.approx(2 * (6000 * 4 / 1e6 + 9000 * 20 / 1e6))
