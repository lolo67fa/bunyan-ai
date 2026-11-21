"""The cumulative experiment budget (BUNYAN_TOTAL_LLM_BUDGET_USD): never reset, fail closed.

No network and no cost: requests are reserved and settled directly, or go through the app with a
stand-in Anthropic client.
"""

import base64
import json
import threading
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
SECRET = "test-session-secret-0123456789-abcdefghijklmnop"
M = 1_000_000  # micro-dollars per dollar
ledger = llm_budget.ledger


@pytest.fixture
def budget(monkeypatch):
    monkeypatch.setenv("BUNYAN_TOTAL_LLM_BUDGET_USD", "5.00")
    monkeypatch.setenv("BUNYAN_LLM_BUDGET_STARTING_SPENT_USD", "0")
    ledger.reset()
    yield
    ledger.reset()


def state():
    return json.loads((storage.DATA_DIR / llm_budget.LEDGER_FILE).read_text(encoding="utf-8"))


def restart():
    """A new process (restart or Railway redeploy): in-memory state is gone, the volume stays."""
    ledger.reset()


# ---------- amounts ----------

def test_amounts_are_exact_integers():
    assert llm_budget.usd_to_micro("5.00") == 5 * M
    assert llm_budget.usd_to_micro("1.2919") == 1_291_900
    assert llm_budget.usd_to_micro("0.0000001") == 1  # rounded up, never down
    assert llm_access.cost_micro(6164, 12429, "claude-opus-5-5") == 6164 * 4 + 12429 * 20 == 273_236
    with pytest.raises(ValueError):
        llm_budget.usd_to_micro("-1")


def test_spending_exactly_five_dollars_then_refused(budget):
    a = ledger.reserve("club", "analysis", 3 * M)
    b = ledger.reserve("club", "analysis", 2 * M)  # exactly 5.00 in total: allowed
    with pytest.raises(llm_budget.BudgetError, match="exhausted"):
        ledger.reserve("club", "analysis", 1)  # one micro-dollar more: refused
    ledger.settle(a, 3 * M)
    ledger.settle(b, 2 * M)
    assert state()["spent_micro"] == 5 * M
    with pytest.raises(llm_budget.BudgetError) as exc:
        ledger.reserve("other", "repair", 1)
    assert exc.value.status == 429 and "انتهت الميزانية" in exc.value.user_message


def test_reconciliation_books_the_real_cost_and_frees_the_rest(budget):
    rid = ledger.reserve("club", "analysis", 720_000)
    assert ledger.settle(rid, 273_236) == 273_236
    s = state()
    assert s["spent_micro"] == 273_236 and s["reserved"] == {}


def test_uncertain_failure_keeps_the_worst_case(budget):
    rid = ledger.reserve("club", "analysis", 720_000)
    assert ledger.settle(rid, None) == 720_000  # timeout / connection error: may have been billed
    assert state()["spent_micro"] == 720_000


def test_concurrent_reservations_cannot_overspend(budget):
    results = []

    def one():
        try:
            results.append(ledger.reserve("club", "analysis", 720_000))
        except llm_budget.BudgetError:
            results.append(None)

    threads = [threading.Thread(target=one) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    granted = [r for r in results if r]
    assert len(granted) == 6  # 6 × 0.72 = 4.32 ≤ 5; a 7th would make 5.04
    assert sum(r["micro"] for r in state()["reserved"].values()) == 6 * 720_000


# ---------- persistence ----------

def test_spending_survives_restart_and_redeploy(budget):
    ledger.settle(ledger.reserve("club", "analysis", 720_000), 273_236)
    restart()
    assert state()["spent_micro"] == 273_236
    ledger.settle(ledger.reserve("club", "analysis", 720_000), 273_236)
    restart()  # redeploy: same volume, same variables
    assert ledger.summary()["spent_usd"] == "0.546472"


def test_a_reservation_interrupted_by_a_restart_is_booked_at_its_worst_case(budget):
    ledger.reserve("club", "analysis", 720_000)  # the process dies before the answer
    restart()
    ledger.check()
    s = state()
    assert s["reserved"] == {} and s["spent_micro"] == 720_000
    assert s["entries"][-1]["kind"] == "recovered"


def test_never_reset_by_new_codes_or_sessions(budget, monkeypatch):
    ledger.settle(ledger.reserve("club", "analysis", 720_000), 4 * M)
    monkeypatch.setenv("BUNYAN_LLM_ACCESS_CODES", "")  # codes rotated
    restart()
    with pytest.raises(llm_budget.BudgetError, match="exhausted"):
        ledger.reserve("brand-new-code", "analysis", 1_100_000)
    monkeypatch.setenv("BUNYAN_LLM_BUDGET_STARTING_SPENT_USD", "0")  # an init variable cannot reset it later
    assert state()["spent_micro"] == 4 * M


def test_starting_balance_is_required_and_recorded(monkeypatch):
    monkeypatch.setenv("BUNYAN_TOTAL_LLM_BUDGET_USD", "5.00")
    monkeypatch.delenv("BUNYAN_LLM_BUDGET_STARTING_SPENT_USD", raising=False)
    ledger.reset()
    with pytest.raises(llm_budget.BudgetError, match="starting balance"):
        ledger.check()
    assert not (storage.DATA_DIR / llm_budget.LEDGER_FILE).exists()
    monkeypatch.setenv("BUNYAN_LLM_BUDGET_STARTING_SPENT_USD", "1.2919")  # historical paid tests
    ledger.check()
    s = ledger.summary()
    assert s["starting_spent_usd"] == "1.291900" and s["remaining_usd"] == "3.708100"


# ---------- fail closed ----------

@pytest.mark.parametrize("damage", ["corrupt", "delete", "sentinel", "negative", "total"])
def test_fail_closed(budget, monkeypatch, damage):
    ledger.check()
    path = storage.DATA_DIR / llm_budget.LEDGER_FILE
    if damage == "corrupt":
        path.write_text("{not json", encoding="utf-8")
    elif damage == "delete":
        path.unlink()  # must not be recreated as a fresh, empty budget
    elif damage == "sentinel":
        (storage.DATA_DIR / llm_budget.SENTINEL_FILE).unlink()
    elif damage == "negative":
        data = state()
        data["spent_micro"] = -1
        path.write_text(json.dumps(data), encoding="utf-8")
    elif damage == "total":
        monkeypatch.setenv("BUNYAN_TOTAL_LLM_BUDGET_USD", "50.00")  # raising the total by a variable
    restart()
    with pytest.raises(llm_budget.BudgetError):
        ledger.reserve("club", "analysis", 1)
    if damage == "delete":
        assert not path.exists()  # never silently recreated
    assert ledger.summary()["available"] is False


def test_not_configured_means_no_paid_requests(monkeypatch):
    monkeypatch.delenv("BUNYAN_TOTAL_LLM_BUDGET_USD", raising=False)
    ledger.reset()
    with pytest.raises(llm_budget.BudgetError, match="not set"):
        ledger.reserve("club", "analysis", 1)


# ---------- through the app: analyses, repairs, several codes ----------

class StandIn:
    def __init__(self):
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **request):
        self.requests.append(request)
        message = SimpleNamespace(stop_reason="end_turn", stop_details=None, _request_id="req_offline",
                                  model="claude-opus-5-5", usage=SimpleNamespace(input_tokens=6164, output_tokens=12429),
                                  content=[SimpleNamespace(type="text", text=REAL.read_text(encoding="utf-8"))])
        return _Ctx(message)


class _Ctx:
    def __init__(self, m):
        self.m = m

    def __enter__(self):
        return SimpleNamespace(get_final_message=lambda: self.m)

    def __exit__(self, *a):
        return False


@pytest.fixture
def site(monkeypatch, budget):
    codes = ",".join(f"{label}:{security.hash_password(code, 1000)}" for label, code in
                     (("tester1", "first-code-2026"), ("tester2", "second-code-2026")))
    env = {
        "BUNYAN_AUTH": "guest", "BUNYAN_SESSION_SECRET": SECRET, "BUNYAN_COOKIE_SECURE": "false", "BA_MODE": "mock",
        "BUNYAN_LLM_ACCESS": "codes", "BUNYAN_LLM_ACCESS_CODES": codes,
        "BA_LLM_PROVIDER": "anthropic", "BA_LLM_MODEL": "claude-opus-5-5", "BA_LLM_BACKEND": "direct",
        "BA_MAX_RETRIES": "0", "BA_SDK_MAX_RETRIES": "0", "BA_FALLBACKS": "off", "BA_MAX_TOKENS": "32000",
        "ANTHROPIC_API_KEY": "sk-ant-offline-test-value-never-sent", "BUNYAN_LLM_DAILY_BUDGET_USD": "5",
        "BUNYAN_LLM_MAX_PER_CODE_PER_DAY": "5", "BUNYAN_MAX_PROJECTS_PER_USER_PER_DAY": "10",
        "BUNYAN_MAX_LLM_ANALYSES_PER_DAY": "20", "BUNYAN_LLM_MAX_ANALYSES_PER_CODE_TOTAL": "2",
        "BUNYAN_USERS": f"ghala:{security.hash_password('admin-password-123', 1000)}", "BUNYAN_ADMINS": "ghala",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    fake = StandIn()
    monkeypatch.setattr(analyst, "_default_llm_generator", lambda d, s: run_direct(d, s, client=fake))
    for reset in (security.guest_sessions.reset, security.limits.reset, security.authenticator.reset,
                  llm_access.access.reset):
        reset()
    with TestClient(main.app):
        pass
    yield fake
    for reset in (security.guest_sessions.reset, security.limits.reset, security.authenticator.reset,
                  llm_access.access.reset):
        reset()


def browser(code):
    c = TestClient(main.app)
    c.get("/llm-access")
    assert c.post("/llm-access", json={"code": code}).status_code == 200
    return c


def test_analyses_from_several_codes_share_one_budget_and_each_code_stops_at_two(site):
    one, two = browser("first-code-2026"), browser("second-code-2026")
    for _ in range(2):
        assert one.post("/projects", json={"prompt": IDEA}).json()["analysis"]["mode"] == "llm"
    third = one.post("/projects", json={"prompt": IDEA})
    assert third.status_code == 429 and "المسموح في التجربة" in third.json()["detail"]
    assert two.post("/projects", json={"prompt": IDEA}).status_code in (200, 201)
    s = ledger.summary()
    assert s["spent_usd"] == "0.819708"  # 3 × 0.273236, real usage, shared by both codes
    assert s["per_code"] == {"tester1": {"analysis": 2}, "tester2": {"analysis": 1}}
    assert len(site.requests) == 3


def test_analysis_and_ai_repair_draw_on_the_same_budget(site):
    one = browser("first-code-2026")
    one.post("/projects", json={"prompt": IDEA})  # 0.273236
    owner = next(iter(json.loads((storage.DATA_DIR / llm_access.STATE_FILE).read_text())["grants"]))
    ticket = llm_access.access.reserve(owner, kind="repair", worst=0.28)
    llm_access.access.settle(ticket, {"input_tokens": 9000, "output_tokens": 700}, "claude-opus-5-5")  # 0.05
    s = ledger.summary()
    assert s["spent_usd"] == "0.323236" and s["per_code"]["tester1"] == {"analysis": 1, "repair": 1}


def test_when_the_total_budget_is_gone_the_site_says_so_and_sends_nothing(site, monkeypatch):
    rid = ledger.reserve("earlier", "analysis", 4_500_000)
    ledger.settle(rid, 4_500_000)  # 0.50 left; one analysis reserves 0.72
    one = browser("first-code-2026")
    r = one.post("/projects", json={"prompt": IDEA})
    assert r.status_code == 429 and "انتهت الميزانية الإجمالية" in r.json()["detail"] and site.requests == []
    guest = TestClient(main.app)  # anonymous guests keep the mock
    assert guest.post("/projects", json={"prompt": "I want a web app to manage my tasks with title, due date, priority and status."}).json()["analysis"]["mode"] == "mock"


def test_a_broken_ledger_hides_the_code_box_and_refuses_paid_requests(site):
    one = browser("first-code-2026")
    (storage.DATA_DIR / llm_budget.LEDGER_FILE).write_text("garbage", encoding="utf-8")
    restart()
    assert one.get("/llm-access").json()["available"] is False
    assert one.post("/projects", json={"prompt": IDEA}).status_code in (429, 503)
    assert site.requests == []


def test_admin_summary_requires_an_admin_and_reveals_no_secrets(site):
    browser("first-code-2026").post("/projects", json={"prompt": IDEA})
    anon = TestClient(main.app)
    assert anon.get("/admin/llm-budget").status_code == 401
    auth = lambda u, p: {"Authorization": "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode()}
    assert anon.get("/admin/llm-budget", headers=auth("ghala", "wrong")).status_code == 401
    r = anon.get("/admin/llm-budget", headers=auth("ghala", "admin-password-123"))
    assert r.status_code == 200 and r.json()["spent_usd"] == "0.273236" and r.json()["total_usd"] == "5.000000"
    text = r.text
    for secret in ("first-code-2026", "sk-ant", "pbkdf2", "guest:", IDEA[:20], SECRET):
        assert secret not in text


def test_codes_on_without_a_total_budget_refuse_to_start(site, monkeypatch):
    monkeypatch.delenv("BUNYAN_TOTAL_LLM_BUDGET_USD")
    with pytest.raises(RuntimeError, match="BUNYAN_TOTAL_LLM_BUDGET_USD"):
        with TestClient(main.app):
            pass


def test_the_budget_alone_does_not_switch_paid_mode_on(monkeypatch, budget):
    monkeypatch.delenv("BUNYAN_LLM_ACCESS", raising=False)
    client = TestClient(main.app)
    assert client.get("/llm-access").json() == {"available": False, "enabled": False}
    assert not (storage.DATA_DIR / llm_budget.LEDGER_FILE).exists()  # not even created until codes are on
