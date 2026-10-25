"""Live evaluation of the real LLM on the sample inputs.

These tests check behaviour, not exact wording: the LLM is non-deterministic.
Every run saves the raw documents and a summary to evals/output/ (git-ignored)
so results can be compared across models and prompt versions.
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.agents.business_analyst import analyze
from backend.agents.business_analyst.config import get_settings
from backend.agents.business_analyst.scope import find_scope_violations

AGENT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# name -> expectations a correct analysis must meet
CASES = {
    "task_manager_en": {
        "status": {"ready_for_review"}, "language": "en",
        "entity_hint": "task", "out_of_scope": set(),
    },
    "inventory_manager_ar": {
        "status": {"ready_for_review"}, "language": "ar",
        "entity_hint": "item|product", "out_of_scope": {"authentication"},
    },
    "appointment_booking_en": {
        "status": {"ready_for_review"}, "language": "en",
        "entity_hint": "appointment|booking", "out_of_scope": {"external_integration"},
    },
    "vague_idea_en": {
        "status": {"needs_clarification"}, "language": "en",
        "entity_hint": None, "out_of_scope": set(),
    },
    "out_of_scope_ar": {
        "status": {"rejected_out_of_scope", "needs_clarification"}, "language": "ar",
        "entity_hint": None, "out_of_scope": {"payments", "native_mobile"},
    },
}

_results = []


@pytest.fixture(scope="module", autouse=True)
def _write_report():
    yield
    if not _results:
        return
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    settings = get_settings("llm")
    report = {"model": settings.litellm_model, "temperature": settings.temperature, "runs": _results}
    (OUTPUT_DIR / f"report-{stamp}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                                     encoding="utf-8")


@pytest.mark.parametrize("name", sorted(CASES))
def test_llm_analysis(name):
    expected = CASES[name]
    request = json.loads((AGENT_DIR / "samples/inputs" / f"{name}.json").read_text(encoding="utf-8"))

    started = time.perf_counter()
    doc = analyze(request["idea"], answers=request.get("answers"), mode="llm")
    seconds = round(time.perf_counter() - started, 1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"{name}.requirements.json").write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    _results.append({
        "sample": name, "seconds": seconds, "status": doc.status,
        "entities": [e.name for e in doc.entities],
        "requirements": len(doc.functional_requirements), "stories": len(doc.user_stories),
        "acceptance_criteria": len(doc.acceptance_criteria),
        "out_of_scope": sorted(i.category for i in doc.out_of_scope),
    })

    # analyze() already guarantees schema validity; these check analysis quality.
    assert doc.status in expected["status"]
    assert doc.language == expected["language"]
    assert find_scope_violations(doc) == []
    assert expected["out_of_scope"] <= {i.category for i in doc.out_of_scope}
    if expected["entity_hint"]:
        assert any(re.search(expected["entity_hint"], e.name, re.IGNORECASE) for e in doc.entities)
        assert len(doc.acceptance_criteria) >= len(doc.user_stories)
    if doc.status == "needs_clarification":
        assert any(q.blocking for q in doc.clarification_questions)
