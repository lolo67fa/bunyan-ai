"""Required fields with a default and the "missing required fields" criterion (AC-2).

A field with a default is pre-filled in the generated form, so "leave all fields empty"
cannot trigger its required-field error. Reported by the QA suite (PR #7, open point T5):
task_manager_en AC-2 expected errors for Priority and Status, which default to
"medium" and "to_do".
"""

import pytest
from pydantic import ValidationError

from backend.agents.business_analyst import analyze
from backend.agents.business_analyst.schema import RequirementsDocument

READY_SAMPLES = [
    "task_manager_en", "inventory_manager_ar", "inventory_dialect_ar", "appointment_booking_en",
    "scenario_a_task_en", "scenario_b_inventory_ar", "scenario_c_booking_ar",
]
MARKERS = ("required field", "حقل إلزامي")


def _required_field_criteria(doc: RequirementsDocument, entity: str):
    stories = {s.id: s.entity for s in doc.user_stories}
    return [a for a in doc.acceptance_criteria
            if stories[a.story_id] == entity and any(m in a.then for m in MARKERS)]


def _listed(criterion) -> set:
    tail = criterion.then.rsplit(":", 1)[1]
    return {part.strip() for part in tail.replace("،", ",").split(",")}


def test_task_manager_ac2_lists_only_title(sample_output):
    doc = RequirementsDocument.model_validate(sample_output("task_manager_en"))
    ac2 = next(a for a in doc.acceptance_criteria if a.id == "AC-2")
    assert ac2.when == 'the user leaves all fields empty and clicks "Save"'
    assert _listed(ac2) == {"Title"}
    assert "Priority" not in ac2.then and "Status" not in ac2.then


def test_defaults_are_unchanged(sample_output):
    defaults = {
        ("task_manager_en", "Task"): {"priority": "medium", "status": "to_do"},
        ("inventory_dialect_ar", "Product"): {"quantity": 0},
        ("inventory_manager_ar", "Item"): {"quantity": 0},
        ("appointment_booking_en", "Appointment"): {"duration_minutes": 30, "status": "scheduled"},
        ("scenario_c_booking_ar", "Booking"): {"status": "مؤكد"},
    }
    for (sample, entity), expected in defaults.items():
        doc = RequirementsDocument.model_validate(sample_output(sample))
        fields = {f.name: f for f in doc.entity(entity).fields}
        for name, value in expected.items():
            assert fields[name].required and fields[name].default == value, (sample, name)


@pytest.mark.parametrize("name", READY_SAMPLES)
def test_required_field_criterion_lists_exactly_the_emptiable_fields(sample_output, name):
    doc = RequirementsDocument.model_validate(sample_output(name))
    for entity in doc.entities:
        emptiable = {f.label for f in entity.fields
                     if f.required and f.default is None and f.type != "boolean"}
        criteria = _required_field_criteria(doc, entity.name)
        if emptiable:
            assert len(criteria) == 1, (name, entity.name)
            assert _listed(criteria[0]) == emptiable, (name, entity.name)
        else:
            assert criteria == [], (name, entity.name)


def test_numeric_default_is_not_listed():
    """Product.quantity defaults to 0 (pre-filled), so only name and price are expected to show errors."""
    doc = analyze("أبغى موقع لإدارة المخزون أضيف المنتجات وأعدل كمياتها وأسعارها", mode="mock")
    product = {f.name: f for f in doc.entity("Product").fields}
    assert product["quantity"].default == 0
    criterion = _required_field_criteria(doc, "Product")[0]
    assert "الكمية" not in _listed(criterion)
    assert _listed(criterion) == {"اسم المنتج", "السعر"}


# --- schema guard: a pre-filled field must not be listed ------------------------------------------

def test_guard_rejects_the_old_ac2(task_doc):
    ac2 = next(a for a in task_doc["acceptance_criteria"] if a["id"] == "AC-2")
    ac2["then"] = "no Task is saved and an error message is shown next to each required field: Title, Priority, Status"
    with pytest.raises(ValidationError, match=r"\['Priority', 'Status'\].*default"):
        RequirementsDocument.model_validate(task_doc)


def test_guard_rejects_arabic_wording(sample_output):
    doc = sample_output("scenario_c_booking_ar")
    stories = {s["id"]: s["entity"] for s in doc["user_stories"]}
    criterion = next(a for a in doc["acceptance_criteria"]
                     if stories[a["story_id"]] == "Booking" and "حقل إلزامي" in a["then"])
    criterion["then"] += "، حالة الحجز"
    with pytest.raises(ValidationError, match="حالة الحجز"):
        RequirementsDocument.model_validate(doc)


def test_guard_ignores_criteria_in_other_wording(task_doc):
    """Only the agent's own required-field wording is checked; other criteria may name defaulted fields."""
    ac = task_doc["acceptance_criteria"][0]
    ac["then"] = 'a Task with Priority "medium" and Status "to_do" appears in the list: Title, Priority, Status'
    RequirementsDocument.model_validate(task_doc)


def test_required_field_without_default_is_still_listed(task_doc):
    """Removing a default makes the field emptiable again, so listing it is correct."""
    for f in task_doc["entities"][0]["fields"]:
        if f["name"] == "priority":
            f.pop("default", None)
    ac2 = next(a for a in task_doc["acceptance_criteria"] if a["id"] == "AC-2")
    ac2["then"] = "no Task is saved and an error message is shown next to each required field: Title, Priority"
    RequirementsDocument.model_validate(task_doc)
