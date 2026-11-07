"""The three evaluation scenarios (A task management, B inventory, C booking) in mock mode.

These tests check that the *mock* templates and the validation pipeline handle the
scenarios correctly. They are NOT evidence that a live LLM analyses them correctly:
that is measured by ``evals/`` with a real model.
"""

import pytest

from backend.agents.business_analyst import analyze
from backend.agents.business_analyst.scope import find_scope_violations

CRUD = ["create", "read", "update", "delete"]


def _run(sample_input, name):
    request = sample_input(name)
    return analyze(request["idea"], mode="mock")


def _fields(doc, entity):
    return {f.name: f for f in doc.entity(entity).fields}


def _assert_consistent(doc):
    """Entities, CRUD operations, requirements, stories and criteria line up."""
    assert doc.status == "ready_for_review"
    assert find_scope_violations(doc) == []
    frs = {r.id: r for r in doc.functional_requirements}
    for entity in doc.entities:
        assert entity.crud.enabled_operations() == CRUD
        for op in CRUD:
            assert any(r.entity == entity.name and r.category == op for r in frs.values()), op
            story = next(s for s in doc.user_stories if s.entity == entity.name and s.operation == op)
            assert doc.criteria_for_story(story.id), f"{story.id} has no criteria"
            assert all(frs[rid].entity in (None, entity.name) for rid in story.requirement_ids)
    assert any(r.category == "persistence" for r in frs.values())
    assert any(a.category == "persistence" for a in doc.acceptance_criteria)
    assert all(q.suggested_default for q in doc.clarification_questions if not q.blocking)


# --- Scenario A: task management ---------------------------------------------------------------

def test_scenario_a_task_management(sample_input):
    doc = _run(sample_input, "scenario_a_task_en")
    _assert_consistent(doc)
    assert doc.language == "en"
    assert [e.name for e in doc.entities] == ["Task"]
    fields = _fields(doc, "Task")
    assert {"title", "description", "due_date", "priority", "status"} <= set(fields)
    assert fields["title"].required and fields["title"].validation.min_length
    assert fields["due_date"].type == "date"
    assert fields["priority"].type == "enum"
    # "mark them as completed" needs a completed value in the status enum.
    assert "done" in fields["status"].enum_values


# --- Scenario B: inventory management (Gulf dialect) -----------------------------------------------

def test_scenario_b_inventory_management(sample_input):
    doc = _run(sample_input, "scenario_b_inventory_ar")
    _assert_consistent(doc)
    assert doc.language == "ar"
    # Categories were not requested, so no Category entity is invented.
    assert [e.name for e in doc.entities] == ["Product"]
    fields = _fields(doc, "Product")
    assert set(fields) == {"name", "quantity", "price"}
    assert fields["quantity"].type == "integer" and fields["quantity"].validation.min_value == 0
    assert fields["price"].type == "decimal" and fields["price"].validation.min_value == 0
    assert not any(f.type == "reference" for f in fields.values())
    # Negative quantity and price have their own failing acceptance criteria.
    invalid = [a.when for a in doc.acceptance_criteria if a.category == "validation"]
    assert any("-1" in w and "الكمية" in w for w in invalid)
    assert any("-5" in w and "السعر" in w for w in invalid)
    assert doc.entity("Product").label == "منتج"


def test_inventory_with_categories_keeps_two_entities(sample_input):
    """Multi-entity output is still produced when the user asks for categories (decision pending)."""
    doc = _run(sample_input, "inventory_manager_ar")
    assert [e.name for e in doc.entities] == ["Category", "Item"]


# --- Scenario C: booking management (Gulf dialect, rules not specified) --------------------------

def test_scenario_c_booking_management(sample_input):
    doc = _run(sample_input, "scenario_c_booking_ar")
    _assert_consistent(doc)
    assert [e.name for e in doc.entities] == ["Booking"]
    fields = _fields(doc, "Booking")
    assert {"customer_name", "date", "time", "status"} <= set(fields)
    assert fields["date"].type == "date" and fields["time"].type == "time"
    assert fields["date"].validation.date_constraint == "not_in_past"
    assert fields["status"].type == "enum" and "ملغى" in fields["status"].enum_values
    # No clinic assumptions (service list, duration) for a generic booking idea.
    assert not {"service", "duration_minutes"} & set(fields)


def test_scenario_c_asks_about_unspecified_business_rules(sample_input):
    doc = _run(sample_input, "scenario_c_booking_ar")
    questions = doc.clarification_questions
    assert len(questions) >= 2 and not any(q.blocking for q in questions)
    text = " ".join(q.question for q in questions)
    assert "إلغاء" in text           # cancel = delete or status change?
    assert "نفس التاريخ والوقت" in text  # double booking allowed?
    # The assumption actually used for cancelling is recorded, and implemented as an update.
    assert any("ملغى" in a for a in doc.assumptions)
    cancel = [r for r in doc.functional_requirements if r.category == "update" and "ملغى" in r.description]
    assert cancel, "cancelling must be a status update, not a hidden delete"
    # No double-booking rule is invented when the user did not ask for one.
    assert not any("نفس التاريخ والوقت" in r.description for r in doc.functional_requirements)


def test_clinic_booking_keeps_the_appointment_template(sample_input):
    doc = _run(sample_input, "appointment_booking_en")
    assert [e.name for e in doc.entities] == ["Appointment"]
