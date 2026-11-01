"""Fixtures for the offline (mock) test suite. Nothing here calls an LLM."""

import json
import os
from pathlib import Path

import pytest

AGENT_DIR = Path(__file__).resolve().parents[1]
SAMPLES = AGENT_DIR / "samples"


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch):
    """Force mock mode and hide any real keys so a test can never spend money."""
    monkeypatch.setenv("BA_MODE", "mock")
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    # Stop config.load_dotenv_if_available() from re-reading a developer's .env.
    monkeypatch.setattr("backend.agents.business_analyst.config.load_dotenv_if_available", lambda: None)


def load_sample_input(name: str) -> dict:
    return json.loads((SAMPLES / "inputs" / f"{name}.json").read_text(encoding="utf-8"))


def load_sample_output(name: str) -> dict:
    return json.loads((SAMPLES / "outputs" / f"{name}.requirements.json").read_text(encoding="utf-8"))


@pytest.fixture
def task_doc() -> dict:
    """A valid ready_for_review document (as a plain dict) to mutate in tests."""
    return load_sample_output("task_manager_en")


@pytest.fixture
def sample_input():
    return load_sample_input


@pytest.fixture
def sample_output():
    return load_sample_output
