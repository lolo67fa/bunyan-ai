"""Consistency rules of requirements.json that protect the Architect, Developer and QA agents.

Each test breaks one rule and checks the exact error, so a passing test proves the
rule itself (not some other validator) rejected the document.
"""

import pytest
from pydantic import ValidationError

from backend.agents.business_analyst.schema import EntityField, RequirementsDocument


def _field(**overrides) -> dict:
    return {"name": "amount", "label": "Amount", "type": "integer", "required": True, **overrides}


# --- defaults must be values the generated form could save -----------------------------------

@pytest.mark.parametrize(
    "field, message",
    [
        (_field(default="ten"), "must be an integer"),
        (_field(default=True), "must be an integer"),
        (_field(default=2.5), "must be an integer"),
        (_field(type="decimal", default="2.5"), "must be a number"),
        (_field(default=-1, validation={"min_value": 0}), "outside its min_value/max_value"),
        (_field(default=300, validation={"max_value": 240}), "outside its min_value/max_value"),
        (_field(type="boolean", default="yes"), "true or false"),
        (_field(type="string", default=5), "must be a string"),
        (_field(type="reference", reference_entity="Category", default="x"), "cannot have a default"),
    ],
)
def test_default_must_match_field_type_and_range(field, message):
    with pytest.raises(ValidationError, match=message):
        EntityField.model_validate(field)


@pytest.mark.parametrize(
    "field",
    [
        _field(default=0, validation={"min_value": 0}),
        _field(type="decimal", default=2.5),
        _field(type="decimal", default=3),
        _field(type="boolean", default=False),
        _field(type="string", default="n/a"),
        _field(type="date", default="2026-01-01"),
    ],
)
def test_valid_defaults_are_accepted(field):
    EntityField.model_validate(field)


# --- user stories stay attached to their own entity --------------------------------------------

def test_story_with_operation_needs_an_entity(task_doc):
    task_doc["user_stories"][0]["entity"] = None
    with pytest.raises(ValidationError, match="has an operation but no entity"):
        RequirementsDocument.model_validate(task_doc)


def test_story_cannot_use_requirements_of_another_entity(sample_output):
    doc = sample_output("inventory_manager_ar")
    stories = {s["entity"]: s for s in doc["user_stories"] if s["operation"] == "create"}
    category_fr = stories["Category"]["requirement_ids"][0]
    stories["Item"]["requirement_ids"].append(category_fr)
    with pytest.raises(ValidationError, match="references requirements of other entities"):
        RequirementsDocument.model_validate(doc)


def test_entity_free_requirement_may_support_any_story(task_doc):
    persistence = next(r["id"] for r in task_doc["functional_requirements"] if r["category"] == "persistence")
    task_doc["user_stories"][1]["requirement_ids"].append(persistence)
    RequirementsDocument.model_validate(task_doc)


# --- a ready document is complete enough to build -------------------------------------------------

def test_ready_document_optional_questions_need_a_default(task_doc):
    task_doc["clarification_questions"][0]["suggested_default"] = None
    with pytest.raises(ValidationError, match="need a suggested_default"):
        RequirementsDocument.model_validate(task_doc)


def test_ready_document_list_view_needs_columns(task_doc):
    task_doc["entities"][0]["crud"]["read"]["list_fields"] = []
    with pytest.raises(ValidationError, match="list_fields is empty"):
        RequirementsDocument.model_validate(task_doc)


# --- nothing from a rejected idea goes downstream --------------------------------------------------

def test_rejected_document_must_not_carry_requirements(task_doc):
    task_doc["status"] = "rejected_out_of_scope"
    task_doc["out_of_scope"] = [{"feature": "Online payments", "category": "payments",
                                 "reason": "Not in the MVP.", "action": "excluded"}]
    with pytest.raises(ValidationError, match="must not contain"):
        RequirementsDocument.model_validate(task_doc)


def test_needs_clarification_may_keep_partial_entities(task_doc):
    """The contract allows a partial model while blocking questions are open."""
    task_doc["status"] = "needs_clarification"
    task_doc["clarification_questions"].append(
        {"id": "Q-9", "question": "Which fields do you need?", "reason": "Fields are unknown.", "blocking": True}
    )
    RequirementsDocument.model_validate(task_doc)
