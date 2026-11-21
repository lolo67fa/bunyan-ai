"""Shared test setup.

- Nothing a test generates may land in the real backend/data.
- The QA stage (Node.js + Playwright + Chromium) is off unless a test asks for
  it, so the fast suites stay offline. Tests that exercise QA either pass a
  runner to run_pipeline or use the ``qa_on`` fixture (tests/test_qa_pipeline.py).
"""

import pytest

from backend import storage


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Point project storage at a fresh temporary folder for every test."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(storage, "DATA_DIR", data_dir)
    return data_dir


@pytest.fixture(autouse=True)
def business_analyst_offline(monkeypatch):
    """Mock mode unless a test says otherwise, and no way to reach a paid model.

    A developer's .env is not read, keys are hidden, and the real LLM call raises:
    LLM-mode tests replace it with a fake generator.
    """
    from backend.agents.business_analyst import analyst, config

    monkeypatch.setenv("BA_MODE", "mock")
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(config, "load_dotenv_if_available", lambda: None)

    def no_paid_calls(description, settings):
        raise AssertionError("a test tried to call the real LLM")

    monkeypatch.setattr(analyst, "_default_llm_generator", no_paid_calls)


@pytest.fixture(autouse=True)
def qa_off_by_default(monkeypatch):
    monkeypatch.setenv("BUNYAN_QA", "off")


@pytest.fixture(autouse=True)
def repair_off_by_default(monkeypatch):
    """The older suites test the pipeline without the repair loop; tests/test_repair_loop.py turns it on."""
    monkeypatch.setenv("BUNYAN_REPAIR", "off")


@pytest.fixture
def qa_on(monkeypatch):
    """Let the pipeline run the real QA Tester for this test."""
    monkeypatch.setenv("BUNYAN_QA", "on")
