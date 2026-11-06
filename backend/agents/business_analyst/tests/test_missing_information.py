"""Missing information: vague ideas must produce blocking clarification questions."""

import pytest
from pydantic import ValidationError

from backend.agents.business_analyst import analyze
from backend.agents.business_analyst.schema import RequirementsDocument


@pytest.mark.parametrize(
    "idea",
    [
        "I want an app to organise my stuff.",
        "Make me a website.",
        "أريد تطبيقاً لتنظيم أموري.",
    ],
)
def test_vague_idea_needs_clarification(idea):
    doc = analyze(idea, mode="mock")
    assert doc.status == "needs_clarification"
    blocking = [q for q in doc.clarification_questions if q.blocking]
    assert len(blocking) >= 1
    assert doc.entities == []
    assert doc.user_stories == []


def test_clarification_questions_use_input_language():
    doc = analyze("أريد تطبيقاً لتنظيم أموري.", mode="mock")
    assert doc.language == "ar"
    assert all(any("؀" <= ch <= "ۿ" for ch in q.question) for q in doc.clarification_questions)


def test_answers_resolve_clarification(sample_input):
    idea = sample_input("vague_idea_en")["idea"]
    first = analyze(idea, mode="mock")
    assert first.status == "needs_clarification"

    answers = {"Q-1": "Tasks for my studies", "Q-2": "Title, due date, priority and status"}
    second = analyze(idea, answers=answers, mode="mock")
    assert second.status == "ready_for_review"
    assert [e.name for e in second.entities] == ["Task"]
    assert not any(q.blocking for q in second.clarification_questions)


def test_needs_clarification_requires_a_blocking_question(task_doc):
    task_doc["status"] = "needs_clarification"
    for q in task_doc["clarification_questions"]:
        q["blocking"] = False
    with pytest.raises(ValidationError, match="blocking question"):
        RequirementsDocument.model_validate(task_doc)


def test_ready_document_cannot_have_open_blocking_questions(task_doc):
    task_doc["clarification_questions"].append(
        {"id": "Q-9", "question": "Which fields do you need?", "reason": "Fields are unknown.", "blocking": True}
    )
    with pytest.raises(ValidationError, match="blocking questions"):
        RequirementsDocument.model_validate(task_doc)


def test_ready_document_needs_entities(task_doc):
    task_doc.update(entities=[], functional_requirements=[], user_stories=[], acceptance_criteria=[])
    with pytest.raises(ValidationError, match="at least one entity"):
        RequirementsDocument.model_validate(task_doc)


def test_clear_idea_records_assumptions_and_optional_questions(sample_input):
    doc = analyze(sample_input("task_manager_en")["idea"], mode="mock")
    assert doc.status == "ready_for_review"
    assert doc.assumptions
    assert doc.clarification_questions and all(not q.blocking for q in doc.clarification_questions)
    assert all(q.suggested_default for q in doc.clarification_questions)


def test_empty_idea_is_rejected():
    with pytest.raises(ValidationError):
        analyze("  ", mode="mock")
