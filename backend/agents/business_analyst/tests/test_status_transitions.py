"""The three analysis statuses and the transitions between them (mock mode).

These are *Business Analyst* statuses inside requirements.json. They are not the
project workflow states (analyzing, awaiting_approval, designing, ...) that the
orchestrator owns; contract/INTEGRATION.md documents how one maps to the other.
"""

import pytest

from backend.agents.business_analyst import analyze
from backend.agents.business_analyst.schema import Status

VAGUE = "I want an app to organise my stuff."


def test_only_the_three_contract_statuses_exist():
    assert set(Status.__args__) == {"ready_for_review", "needs_clarification", "rejected_out_of_scope"}


def test_needs_clarification_has_no_final_requirements():
    doc = analyze(VAGUE, mode="mock")
    assert doc.status == "needs_clarification"
    assert any(q.blocking for q in doc.clarification_questions)
    assert doc.entities == [] and doc.functional_requirements == [] and doc.acceptance_criteria == []


def test_clarification_then_answers_gives_ready_for_review():
    first = analyze(VAGUE, mode="mock")
    blocking = [q.id for q in first.clarification_questions if q.blocking]
    answers = {blocking[0]: "Products in my shop", blocking[1]: "Name, quantity and price"}
    second = analyze(VAGUE, answers=answers, mode="mock")
    assert second.status == "ready_for_review"
    assert second.source_idea == VAGUE  # the original idea is kept, answers are extra input
    assert second.acceptance_criteria


def test_unhelpful_answers_keep_needs_clarification():
    doc = analyze(VAGUE, answers={"Q-1": "not sure", "Q-2": "some info"}, mode="mock")
    assert doc.status == "needs_clarification"


def test_blank_answers_do_not_resolve_clarification():
    doc = analyze(VAGUE, answers={"Q-1": " ", "Q-2": ""}, mode="mock")
    assert doc.status == "needs_clarification"


def test_out_of_scope_only_idea_is_rejected_with_reasons(sample_input):
    doc = analyze(sample_input("out_of_scope_ar")["idea"], mode="mock")
    assert doc.status == "rejected_out_of_scope"
    assert doc.out_of_scope and all(i.reason for i in doc.out_of_scope)
    assert doc.entities == [] and doc.functional_requirements == []


def test_rejected_idea_can_become_ready_when_answers_add_crud_content(sample_input):
    idea = sample_input("out_of_scope_ar")["idea"]
    doc = analyze(idea, answers={"Q-1": "أبغى أسجل المنتجات وكمياتها في المخزون"}, mode="mock")
    assert doc.status == "ready_for_review"
    # The unsupported features stay listed as out of scope; they do not become requirements.
    assert {"payments", "native_mobile", "realtime_collaboration"} <= {i.category for i in doc.out_of_scope}


@pytest.mark.parametrize(
    "idea",
    [
        "A recipe app where I record recipes and ingredients, and share it with friends",
        "An app to track my books, and I also want users to log in with a password",
    ],
)
def test_crud_idea_with_out_of_scope_extras_is_not_rejected(idea):
    """Unknown domain + out-of-scope extras: ask (mock cannot model it) instead of rejecting."""
    doc = analyze(idea, mode="mock")
    assert doc.status == "needs_clarification"
    assert doc.out_of_scope


def test_ready_for_review_waits_for_human_approval(sample_input):
    """The agent only returns the document; it never loads or triggers the Architect itself."""
    import sys

    doc = analyze(sample_input("scenario_a_task_en")["idea"], mode="mock")
    assert doc.status == "ready_for_review"
    assert not any(name.startswith("backend.agents.architect") for name in sys.modules)
