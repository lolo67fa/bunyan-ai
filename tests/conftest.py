"""Shared test setup: nothing a test generates may land in the real backend/data."""

import pytest

from backend import storage


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Point project storage at a fresh temporary folder for every test."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(storage, "DATA_DIR", data_dir)
    return data_dir
