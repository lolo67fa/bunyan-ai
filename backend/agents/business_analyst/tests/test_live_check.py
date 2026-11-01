"""The live-test runner (live_check.py), exercised with a FAKE client: no network, no cost."""

import json
from types import SimpleNamespace

import pytest

from backend.agents.business_analyst.config import Settings
from backend.agents.business_analyst.live_check import DEFAULT_IDEA, run, single_call_problems
from backend.agents.business_analyst.mock_analyst import mock_generate

FAKE_KEY = "sk-ant-offline-test-value-never-sent"


def _settings(**overrides):
    base = dict(mode="llm", provider="anthropic", model="claude-opus-5-5", temperature=None, max_retries=0,
                verbose=False, backend="direct", effort="high", fallbacks=False, sdk_max_retries=0)
    base.update(overrides)
    return Settings(**base)


class FakeAnthropic:
    def __init__(self, answers, fail_preflight=False):
        self.answers = list(answers)
        self.fail_preflight = fail_preflight
        self.stream_requests = []
        self.models = SimpleNamespace(retrieve=self._retrieve)
        self.messages = SimpleNamespace(count_tokens=lambda **kw: SimpleNamespace(input_tokens=12345))
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _retrieve(self, model):
        if self.fail_preflight:
            raise RuntimeError("NotFoundError: model not found")
        return SimpleNamespace(id=model, display_name="Claude Opus 5.5")

    def _stream(self, **request):
        self.stream_requests.append(request)
        message = SimpleNamespace(
            model=request["model"], stop_reason="end_turn", stop_details=None, _request_id="req_fake",
            usage=SimpleNamespace(input_tokens=12345, output_tokens=9000,
                                  cache_creation_input_tokens=0, cache_read_input_tokens=0),
            content=[SimpleNamespace(type="text", text=self.answers.pop(0))],
        )
        return _Ctx(SimpleNamespace(get_final_message=lambda: message))


class _Ctx:
    def __init__(self, inner):
        self.inner = inner

    def __enter__(self):
        return self.inner

    def __exit__(self, *exc):
        return False


@pytest.fixture(autouse=True)
def _fake_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)


def _read(out):
    return json.loads((out / "summary.json").read_text(encoding="utf-8"))


def test_successful_run_makes_exactly_one_request(tmp_path):
    client = FakeAnthropic([mock_generate(DEFAULT_IDEA, "ar")])
    assert run(DEFAULT_IDEA, tmp_path, client=client, settings=_settings()) == 0
    summary = _read(tmp_path)
    assert summary["result"] == "passed" and summary["paid_requests"] == 1
    assert len(client.stream_requests) == 1
    request = client.stream_requests[0]
    assert "fallbacks" not in request and "betas" not in request
    assert all(summary["checks"].values())
    assert summary["estimated_cost_usd"] == round(12345 * 4 / 1e6 + 9000 * 20 / 1e6, 4)
    assert (tmp_path / "requirements.json").exists()


def test_outputs_never_contain_the_api_key(tmp_path):
    run(DEFAULT_IDEA, tmp_path, client=FakeAnthropic([mock_generate(DEFAULT_IDEA, "ar")]), settings=_settings())
    for path in tmp_path.iterdir():
        assert FAKE_KEY not in path.read_text(encoding="utf-8")
    assert _read(tmp_path)["api_key_present"] is True


def test_invalid_answer_is_not_retried(tmp_path):
    client = FakeAnthropic(['{"status": "ready_for_review"}', mock_generate(DEFAULT_IDEA, "ar")])
    assert run(DEFAULT_IDEA, tmp_path, client=client, settings=_settings()) == 1
    summary = _read(tmp_path)
    assert summary["result"] == "analysis_failed" and summary["validation_errors"]
    assert len(client.stream_requests) == 1
    assert (tmp_path / "raw_output.txt").exists()


def test_preflight_failure_makes_no_paid_request(tmp_path):
    client = FakeAnthropic([mock_generate(DEFAULT_IDEA, "ar")], fail_preflight=True)
    assert run(DEFAULT_IDEA, tmp_path, client=client, settings=_settings()) == 1
    assert _read(tmp_path)["result"] == "preflight_failed"
    assert client.stream_requests == []


@pytest.mark.parametrize(
    "overrides",
    [{"max_retries": 2}, {"fallbacks": True}, {"sdk_max_retries": None}, {"sdk_max_retries": 2},
     {"backend": "crewai"}],
)
def test_unsafe_settings_stop_before_any_call(tmp_path, overrides):
    client = FakeAnthropic([mock_generate(DEFAULT_IDEA, "ar")])
    assert run(DEFAULT_IDEA, tmp_path, client=client, settings=_settings(**overrides)) == 2
    assert _read(tmp_path)["result"] == "configuration_error"
    assert client.stream_requests == []
    assert single_call_problems(_settings(**overrides))


def test_missing_key_stops_before_any_call(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert run(DEFAULT_IDEA, tmp_path, settings=_settings()) == 2
    assert _read(tmp_path)["error"] == "ANTHROPIC_API_KEY is not set"
