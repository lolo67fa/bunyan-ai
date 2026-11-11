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
def qa_off_by_default(monkeypatch):
    monkeypatch.setenv("BUNYAN_QA", "off")


@pytest.fixture
def qa_on(monkeypatch):
    """Let the pipeline run the real QA Tester for this test."""
    monkeypatch.setenv("BUNYAN_QA", "on")
