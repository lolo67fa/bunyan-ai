"""Input contract of the Business Analyst Agent: ``idea`` (+ optional ``answers`` / ``feedback``).

``idea`` is the canonical name, matching the frontend (``frontend/src/api/httpClient.js``).
``prompt`` is a deprecated alias accepted only because the current FastAPI skeleton
(``backend/schemas/contracts.py``) uses it.
"""

import pytest
from pydantic import ValidationError

from backend.agents.business_analyst import AnalystInput, analyze, analyze_input
from backend.agents.business_analyst.schema import MAX_ANSWER_LENGTH, MAX_ANSWERS, MAX_IDEA_LENGTH

TASK_IDEA = "A task manager with title, due date and status"


# --- canonical name and legacy alias ---------------------------------------------------------

def test_idea_is_the_canonical_field():
    request = AnalystInput.model_validate({"idea": TASK_IDEA})
    assert request.idea == TASK_IDEA
    assert "idea" in request.model_dump() and "prompt" not in request.model_dump()


def test_legacy_prompt_is_mapped_to_idea():
    request = AnalystInput.model_validate({"prompt": TASK_IDEA})
    assert request.idea == TASK_IDEA
    assert "prompt" not in request.model_dump()


def test_idea_and_prompt_with_the_same_value_are_accepted():
    assert AnalystInput.model_validate({"idea": TASK_IDEA, "prompt": TASK_IDEA}).idea == TASK_IDEA


def test_conflicting_idea_and_prompt_are_rejected():
    with pytest.raises(ValidationError, match="differ"):
        AnalystInput.model_validate({"idea": TASK_IDEA, "prompt": "Something else entirely"})


def test_unknown_keys_are_still_rejected():
    with pytest.raises(ValidationError):
        AnalystInput.model_validate({"idea": TASK_IDEA, "text": TASK_IDEA})


def test_public_analyze_signature_is_unchanged():
    """The orchestrator can keep calling analyze(idea, answers=..., feedback=...)."""
    doc = analyze(TASK_IDEA, answers={}, feedback=None, mode="mock")
    assert doc.status == "ready_for_review"
    assert doc.source_idea == TASK_IDEA
    assert analyze_input(AnalystInput(prompt=TASK_IDEA), mode="mock") == doc


def test_frontend_payload_shape_is_accepted():
    """POST /projects body sent by the frontend today: {"idea": "..."}."""
    assert analyze_input(AnalystInput.model_validate({"idea": TASK_IDEA}), mode="mock").status == "ready_for_review"


# --- idea validation ------------------------------------------------------------------------

@pytest.mark.parametrize("payload", [{}, {"idea": None}, {"idea": 123}, {"idea": ["a task app"]}, {"idea": {"x": 1}}])
def test_missing_or_wrongly_typed_idea_is_rejected(payload):
    with pytest.raises(ValidationError):
        AnalystInput.model_validate(payload)


@pytest.mark.parametrize("idea", ["", "   ", "\n\t", "ab"])
def test_empty_or_too_short_idea_is_rejected(idea):
    with pytest.raises(ValidationError):
        AnalystInput(idea=idea)


@pytest.mark.parametrize("idea", ["!!!???", "12345", "... --- ..."])
def test_idea_without_words_is_rejected(idea):
    with pytest.raises(ValidationError, match="in words"):
        AnalystInput(idea=idea)


def test_overlong_idea_is_rejected():
    AnalystInput(idea="a" * MAX_IDEA_LENGTH)
    with pytest.raises(ValidationError):
        AnalystInput(idea="a" * (MAX_IDEA_LENGTH + 1))


def test_frontend_maximum_fits_the_agent_limit():
    """frontend/src/pages/IdeaPage.jsx allows 2000 characters; the agent must accept them."""
    assert MAX_IDEA_LENGTH >= 2000


@pytest.mark.parametrize(
    "idea, language",
    [
        ("أبغى موقع لإدارة المهام", "ar"),
        ("I want a website to manage my tasks", "en"),
        ("تطبيق لإدارة المهام with due dates", "ar"),
    ],
)
def test_arabic_english_and_mixed_ideas_are_accepted(idea, language):
    doc = analyze(idea, mode="mock")
    assert doc.language == language
    assert doc.source_idea == idea


def test_idea_whitespace_is_trimmed_and_preserved_otherwise():
    doc = analyze("   " + TASK_IDEA + "  \n", mode="mock")
    assert doc.source_idea == TASK_IDEA


# --- answers and feedback ------------------------------------------------------------------

def test_blank_answers_are_treated_as_unanswered():
    request = AnalystInput(idea=TASK_IDEA, answers={"Q-1": "  ", "Q-2": " Tasks "})
    assert request.answers == {"Q-2": "Tasks"}


def test_answer_keys_must_not_be_blank():
    with pytest.raises(ValidationError, match="question id"):
        AnalystInput(idea=TASK_IDEA, answers={" ": "Tasks"})


@pytest.mark.parametrize("answers", [{"Q-1": 5}, {"Q-1": None}, ["Tasks"], "Tasks"])
def test_wrongly_typed_answers_are_rejected(answers):
    with pytest.raises(ValidationError):
        AnalystInput(idea=TASK_IDEA, answers=answers)


def test_answer_count_and_length_are_limited():
    with pytest.raises(ValidationError, match="at most"):
        AnalystInput(idea=TASK_IDEA, answers={f"Q-{i}": "x" for i in range(MAX_ANSWERS + 1)})
    with pytest.raises(ValidationError, match="longer than"):
        AnalystInput(idea=TASK_IDEA, answers={"Q-1": "x" * (MAX_ANSWER_LENGTH + 1)})


def test_blank_feedback_becomes_none():
    assert AnalystInput(idea=TASK_IDEA, feedback="   ").feedback is None


def test_repeated_identical_requests_give_identical_documents():
    answers = {"Q-1": "Tasks for my studies", "Q-2": "Title, due date and status"}
    first = analyze("I want an app to organise my stuff.", answers=answers, mode="mock")
    second = analyze("I want an app to organise my stuff.", answers=dict(answers), mode="mock")
    assert first == second
