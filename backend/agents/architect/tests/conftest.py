import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def requirements():
    """Load a Business Analyst sample (copied from feature/ghala-analyst @ 8d58aa8)."""

    def _load(name: str) -> dict:
        return json.loads((FIXTURES / f"{name}.requirements.json").read_text(encoding="utf-8"))

    return _load
