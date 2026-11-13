"""Fixtures for the offline test suite. Nothing here calls a real LLM."""

import json
from pathlib import Path

import pytest

AGENT_DIR = Path(__file__).resolve().parents[1]
SAMPLES = AGENT_DIR / "samples"
SAMPLE_NAMES = ["inventory_dialect_ar", "task_manager_en", "appointment_tests_failing_en", "stopped_at_structure_ar"]


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch):
    """Force rules mode and hide any real key so a test can never spend money."""
    monkeypatch.setenv("PM_MODE", "rules")
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "LLM_MODEL", "PM_LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr("backend.agents.project_manager.config.load_dotenv_if_available", lambda: None)


def load_input(name: str) -> dict:
    return json.loads((SAMPLES / "inputs" / f"{name}.json").read_text(encoding="utf-8"))
