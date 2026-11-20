"""What the API needs from the agent in LLM mode: settings, revisions, safe errors.

All offline: fake clients and constructed SDK exceptions, no network, no API key, no cost.
"""

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.agents.business_analyst import analyze
from backend.agents.business_analyst.analyst import AnalysisError
from backend.agents.business_analyst.config import ConfigError, Settings, get_settings
from backend.agents.business_analyst.direct_llm import LLMRefusal, build_request, run_direct
from backend.agents.business_analyst.errors import describe_failure
from backend.agents.business_analyst.prompts import build_task_description
from backend.agents.business_analyst.revision import summarize_revision
from backend.agents.business_analyst.schema import AnalystInput

SECRET = "sk-ant-offline-test-value-never-sent"


def _settings(**overrides):
    base = dict(mode="llm", provider="anthropic", model="claude-opus-5-5", temperature=None,
                max_retries=0, verbose=False, backend="direct", effort="high")
    base.update(overrides)
    return Settings(**base)


# ---------- settings ----------

def test_default_mode_is_mock_and_defaults_are_bounded(monkeypatch):
    settings = get_settings()
    assert settings.mode == "mock"
    assert settings.request_timeout == 300.0 and settings.max_tokens == 64000


def test_timeout_and_token_cap_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("BA_REQUEST_TIMEOUT", "120")
    monkeypatch.setenv("BA_MAX_TOKENS", "32000")
    settings = get_settings()
    assert settings.request_timeout == 120.0 and settings.max_tokens == 32000


@pytest.mark.parametrize("name, value", [
    ("BA_MODE", "real"), ("BA_REQUEST_TIMEOUT", "0"), ("BA_REQUEST_TIMEOUT", "soon"),
    ("BA_MAX_TOKENS", "-5"), ("BA_MAX_TOKENS", "lots"), ("BA_MAX_RETRIES", "two"), ("BA_SDK_MAX_RETRIES", "-1"),
])
def test_invalid_settings_are_clear_config_errors(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigError, match=name):
        get_settings()


def test_llm_mode_without_a_key_is_a_config_error_before_any_call():
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        _settings().check_llm_ready()


# ---------- direct backend ----------

class _FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return SimpleNamespace(get_final_message=lambda: self.message)

    def __exit__(self, *exc):
        return False


def test_direct_backend_uses_the_token_cap_and_request_timeout(monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    created, requests = [], []

    class FakeAnthropic:
        def __init__(self, **options):
            created.append(options)
            self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

        def _stream(self, **request):
            requests.append(request)
            return _FakeStream(SimpleNamespace(stop_reason="end_turn", stop_details=None, _request_id="req_x",
                                               content=[SimpleNamespace(type="text", text="{}")]))

    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    run_direct("prompt", _settings(request_timeout=90.0, max_tokens=20000, sdk_max_retries=0))
    assert created == [{"timeout": 90.0, "max_retries": 0}]
    assert requests[0]["max_tokens"] == 20000 or requests[0]["extra_body"]  # older SDKs: see adapt_to_sdk
    assert build_request("p", _settings(max_tokens=20000))["max_tokens"] == 20000


# ---------- feedback reaches the model with the reviewed version ----------

def test_feedback_prompt_carries_the_reviewed_requirements(task_doc):
    text = build_task_description("Task app", "en", {"Q-1": "Students"}, "Add a phone number field",
                                  previous_requirements=task_doc)
    assert "CURRENT requirements.json" in text and json.dumps(task_doc["entities"][0]["name"]) in text
    assert "Add a phone number field" in text and "- Q-1: Students" in text
    assert "Revise the CURRENT requirements according to the feedback" in text


def test_no_revision_instruction_without_feedback(task_doc):
    text = build_task_description("Task app", "en", previous_requirements=task_doc)
    assert "Revise the CURRENT requirements" not in text


def test_prompt_asks_for_exactly_one_entity():
    text = build_task_description("Shop with products and categories", "en")
    assert "exactly ONE entity" in text and 'Relations between entities use type "reference"' not in text


def test_analyze_sends_previous_requirements_to_the_generator(task_doc):
    seen = []

    def generator(description, settings):
        seen.append(description)
        return json.dumps(task_doc)

    analyze(task_doc["source_idea"], feedback="Add a notes field", mode="llm", settings=_settings(),
            llm_generator=generator, previous_requirements=task_doc)
    assert "CURRENT requirements.json" in seen[0] and "Add a notes field" in seen[0]


def test_mock_mode_ignores_previous_requirements(task_doc):
    doc = analyze("I want a task manager app", feedback="Add a phone field", previous_requirements=task_doc)
    assert doc.status == "ready_for_review"  # mock answers from its template; the revision summary shows no change


# ---------- revision summary ----------

def test_revision_lists_an_added_field(task_doc):
    revised = json.loads(json.dumps(task_doc))
    revised["entities"][0]["fields"].append({"name": "phone", "label": "Phone", "type": "phone", "required": False})
    summary = summarize_revision(task_doc, revised)
    assert summary["changed"] is True
    assert summary["added_fields"] == [{"entity": "Task", "field": "phone", "label": "Phone"}]
    assert summary["removed_fields"] == [] and summary["changed_fields"] == []


def test_revision_reports_an_unchanged_document(task_doc):
    same = json.loads(json.dumps(task_doc))
    same["source_idea"] = "a different wording of the idea"
    summary = summarize_revision(task_doc, same)
    assert summary["changed"] is False and summary["added_fields"] == []


def test_revision_reports_removed_and_changed_fields(task_doc):
    revised = json.loads(json.dumps(task_doc))
    fields = revised["entities"][0]["fields"]
    removed = fields.pop()
    fields[0]["required"] = not fields[0].get("required")
    summary = summarize_revision(task_doc, revised)
    assert [f["field"] for f in summary["removed_fields"]] == [removed["name"]]
    assert summary["changed_fields"][0]["changed"] == ["required"]


# ---------- safe errors ----------

def _status_error(cls, status):
    import httpx

    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status, request=request, headers={"request-id": "req_123"})
    return cls(f"status {status}", response=response, body=None)


@pytest.mark.parametrize("name, status, code, retryable", [
    ("AuthenticationError", 401, "llm_auth_failed", False),
    ("PermissionDeniedError", 403, "llm_auth_failed", False),
    ("NotFoundError", 404, "llm_model_unavailable", False),
    ("BadRequestError", 400, "llm_bad_request", False),
    ("RateLimitError", 429, "llm_rate_limited", True),
    ("InternalServerError", 500, "llm_unavailable", True),
    ("APIStatusError", 529, "llm_unavailable", True),
])
def test_sdk_status_errors_become_safe_codes(name, status, code, retryable):
    anthropic = pytest.importorskip("anthropic")
    failure = describe_failure(_status_error(getattr(anthropic, name), status))
    assert (failure.code, failure.retryable) == (code, retryable)
    assert "req_123" in failure.detail and failure.message and not failure.message.isascii()


def test_timeout_and_network_errors():
    anthropic = pytest.importorskip("anthropic")
    import httpx

    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    assert describe_failure(anthropic.APITimeoutError(request=request)).code == "llm_timeout"
    assert describe_failure(anthropic.APIConnectionError(request=request)).code == "llm_unavailable"


def test_agent_failures_become_safe_codes(task_doc):
    assert describe_failure(ConfigError("BA_MODE must be 'mock' or 'llm'")).code == "ba_not_configured"
    assert describe_failure(AnalysisError("invalid", ["entities: missing"])).code == "ba_invalid_output"
    with pytest.raises(ValidationError) as bad_input:
        AnalystInput(idea="!!")
    assert describe_failure(bad_input.value).code == "invalid_input"
    for text, code in [("model refused the request", "ba_refused"), ("cut off at max_tokens=64000", "ba_output_truncated")]:
        try:
            try:
                raise LLMRefusal(text)
            except LLMRefusal as cause:
                raise AnalysisError("the model did not return a usable answer", [str(cause)]) from cause
        except AnalysisError as exc:
            assert describe_failure(exc).code == code
    assert describe_failure(RuntimeError(SECRET)).code == "ba_failed"


def test_no_secret_reaches_the_user_message_or_the_log_detail():
    failure = describe_failure(RuntimeError(f"boom {SECRET}"))
    assert SECRET not in failure.message and SECRET not in failure.detail
    assert SECRET not in json.dumps(failure.as_error(), ensure_ascii=False)


def test_invalid_llm_json_is_retried_then_reported(task_doc):
    calls = []

    def generator(description, settings):
        calls.append(description)
        return "this is not JSON"

    with pytest.raises(AnalysisError) as exc:
        analyze("I want a task manager app", mode="llm", settings=_settings(max_retries=1), llm_generator=generator)
    assert len(calls) == 2 and "rejected by the validator" in calls[1]
    assert describe_failure(exc.value).code == "ba_invalid_output"
