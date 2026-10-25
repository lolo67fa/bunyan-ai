"""Direct Anthropic SDK backend, tested with a FAKE client (no network, no API key, no cost)."""

import json
from types import SimpleNamespace

import pytest

from backend.agents.business_analyst import analyze
from backend.agents.business_analyst.analyst import AnalysisError
from backend.agents.business_analyst.config import ConfigError, Settings, get_settings
from backend.agents.business_analyst.direct_llm import build_request, run_direct
from backend.agents.business_analyst.mock_analyst import mock_generate

IDEA = "أبغى موقع لإدارة المخزون أقدر أضيف فيه المنتجات وأعدل كمياتها وأسعارها وأحذفها."


def _settings(**overrides):
    base = dict(mode="llm", provider="anthropic", model="claude-opus-5-5", temperature=None,
                max_retries=2, verbose=False, backend="direct", effort="high")
    base.update(overrides)
    return Settings(**base)


class FakeClient:
    """Mimics client.beta.messages.stream(...) -> context manager -> get_final_message()."""

    def __init__(self, texts, stop_reason="end_turn"):
        self.texts = list(texts)
        self.stop_reason = stop_reason
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **request):
        self.requests.append(request)
        message = SimpleNamespace(
            stop_reason=self.stop_reason, stop_details=None, _request_id="req_test",
            content=[SimpleNamespace(type="thinking", thinking=""),
                     SimpleNamespace(type="text", text=self.texts.pop(0))],
        )
        return _Ctx(message)


class _Ctx:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return SimpleNamespace(get_final_message=lambda: self.message)

    def __exit__(self, *exc):
        return False


def test_request_never_sends_sampling_parameters():
    request = build_request("prompt", _settings(temperature=0.2))
    assert not {"temperature", "top_p", "top_k"} & set(request)


def test_request_shape_for_opus():
    request = build_request("prompt", _settings())
    assert request["model"] == "claude-opus-5-5"
    assert request["output_config"] == {"effort": "high"}
    assert request["fallbacks"] == "default" and request["betas"] == ["server-side-fallback-2026-07-01"]
    assert request["messages"] == [{"role": "user", "content": "prompt"}]
    assert "Business Analyst" in request["system"]


def test_fallback_only_on_models_that_support_it():
    request = build_request("prompt", _settings(model="claude-haiku-5-5"))
    assert "fallbacks" not in request and "betas" not in request


def test_provider_prefixed_model_is_accepted():
    assert build_request("p", _settings(model="anthropic/claude-opus-5-5"))["model"] == "claude-opus-5-5"


def test_direct_backend_rejects_other_providers():
    with pytest.raises(ConfigError):
        build_request("p", _settings(provider="openai", model="some-model"))


def test_run_direct_returns_text_blocks_only():
    client = FakeClient(['{"a": 1}'])
    assert run_direct("prompt", _settings(), client=client) == '{"a": 1}'


def test_full_pipeline_with_fake_claude_on_dialect_input():
    client = FakeClient([mock_generate(IDEA, "ar")])
    doc = analyze(IDEA, settings=_settings(),
                  llm_generator=lambda prompt, s: run_direct(prompt, s, client=client))
    assert doc.language == "ar" and doc.status == "ready_for_review"
    assert IDEA in client.requests[0]["messages"][0]["content"]


def test_refusal_becomes_analysis_error():
    client = FakeClient(["{}"], stop_reason="refusal")
    with pytest.raises(AnalysisError, match="refused"):
        analyze(IDEA, settings=_settings(),
                llm_generator=lambda prompt, s: run_direct(prompt, s, client=client))


def test_truncated_answer_becomes_analysis_error():
    client = FakeClient(["{"], stop_reason="max_tokens")
    with pytest.raises(AnalysisError, match="max_tokens"):
        analyze(IDEA, settings=_settings(),
                llm_generator=lambda prompt, s: run_direct(prompt, s, client=client))


def test_backend_and_effort_from_environment(monkeypatch):
    monkeypatch.setenv("BA_LLM_BACKEND", "direct")
    monkeypatch.setenv("BA_EFFORT", "medium")
    monkeypatch.delenv("BA_TEMPERATURE", raising=False)
    settings = get_settings("llm")
    assert (settings.backend, settings.effort, settings.temperature) == ("direct", "medium", None)


@pytest.mark.parametrize("var, value", [("BA_LLM_BACKEND", "langchain"), ("BA_EFFORT", "extreme")])
def test_invalid_backend_or_effort(monkeypatch, var, value):
    monkeypatch.setenv(var, value)
    with pytest.raises(ConfigError):
        get_settings("llm")


def test_auth_token_satisfies_credential_check(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "dummy-token-for-test")
    _settings().check_llm_ready()
