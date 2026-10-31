"""Schema validity: the contract accepts good documents and rejects broken ones."""

import copy
import json

import pytest
from pydantic import ValidationError

from backend.agents.business_analyst.schema import (
    SCHEMA_VERSION,
    AcceptanceCriterion,
    EntityField,
    RequirementsDocument,
    json_schema,
)

ALL_SAMPLES = [
    "task_manager_en",
    "inventory_manager_ar",
    "inventory_dialect_ar",
    "appointment_booking_en",
    "vague_idea_en",
    "out_of_scope_ar",
]


@pytest.mark.parametrize("name", ALL_SAMPLES)
def test_sample_outputs_are_valid(sample_output, name):
    doc = RequirementsDocument.model_validate(sample_output(name))
    assert doc.schema_version == SCHEMA_VERSION


def test_round_trip_through_json(task_doc):
    doc = RequirementsDocument.model_validate(task_doc)
    again = RequirementsDocument.model_validate_json(doc.model_dump_json())
    assert again == doc


def test_ready_document_covers_all_crud_operations(task_doc):
    doc = RequirementsDocument.model_validate(task_doc)
    task = doc.entity("Task")
    assert task.crud.enabled_operations() == ["create", "read", "update", "delete"]
    assert {s.operation for s in doc.user_stories} == {"create", "read", "update", "delete"}
    for story in doc.user_stories:
        assert doc.criteria_for_story(story.id), f"{story.id} has no acceptance criteria"


def test_json_schema_export_is_marked_as_proposal():
    schema = json_schema()
    assert "PROPOSAL" in schema["title"]
    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    json.dumps(schema)  # serialisable


def _mutate(doc: dict, fn) -> dict:
    doc = copy.deepcopy(doc)
    fn(doc)
    return doc


BROKEN = {
    "unknown top-level key": lambda d: d.update(extra_key=1),
    "wrong schema version": lambda d: d.update(schema_version="9.9"),
    "unknown status": lambda d: d.update(status="done"),
    "entity without fields": lambda d: d["entities"][0].update(fields=[]),
    "entity name not PascalCase": lambda d: d["entities"][0].update(name="task item"),
    "field name not snake_case": lambda d: d["entities"][0]["fields"][0].update(name="Title"),
    "reserved field id": lambda d: d["entities"][0]["fields"][0].update(name="id"),
    "unsupported field type": lambda d: d["entities"][0]["fields"][0].update(type="password"),
    "enum without values": lambda d: d["entities"][0]["fields"][3].update(enum_values=None),
    "enum default not in values": lambda d: d["entities"][0]["fields"][3].update(default="urgent"),
    "min_length > max_length": lambda d: d["entities"][0]["fields"][0]["validation"].update(min_length=200),
    "numeric rule on text field": lambda d: d["entities"][0]["fields"][0]["validation"].update(min_value=1),
    "invalid regex pattern": lambda d: d["entities"][0]["fields"][0]["validation"].update(pattern="(["),
    "display_field unknown": lambda d: d["entities"][0].update(display_field="name"),
    "list field unknown": lambda d: d["entities"][0]["crud"]["read"].update(list_fields=["nope"]),
    "create disabled": lambda d: d["entities"][0]["crud"]["create"].update(enabled=False),
    "duplicate requirement id": lambda d: d["functional_requirements"][1].update(id="FR-1"),
    "story references unknown requirement": lambda d: d["user_stories"][0].update(requirement_ids=["FR-99"]),
    "criterion references unknown story": lambda d: d["acceptance_criteria"][0].update(story_id="US-99"),
    "story without criteria": lambda d: d.update(
        acceptance_criteria=[a for a in d["acceptance_criteria"] if a["story_id"] != "US-4"]
    ),
    "CRUD operation without requirement": lambda d: d.update(
        functional_requirements=[r for r in d["functional_requirements"] if r["category"] != "delete"],
        user_stories=[s for s in d["user_stories"] if s["operation"] != "delete"],
        acceptance_criteria=[a for a in d["acceptance_criteria"] if a["story_id"] != "US-4"],
    ),
    "no entity supports all four operations": lambda d: d["entities"][0]["crud"]["delete"].update(enabled=False),
    "vague acceptance criterion": lambda d: d["acceptance_criteria"][0].update(then="the page is user-friendly"),
    "vague Arabic acceptance criterion": lambda d: d["acceptance_criteria"][0].update(then="تظهر الصفحة بشكل سهل"),
    "bad requirement id format": lambda d: d["functional_requirements"][0].update(id="REQ1"),
}


@pytest.mark.parametrize("case", sorted(BROKEN))
def test_broken_documents_are_rejected(task_doc, case):
    with pytest.raises(ValidationError):
        RequirementsDocument.model_validate(_mutate(task_doc, BROKEN[case]))


def test_reference_field_must_point_to_existing_entity(sample_output):
    doc = sample_output("inventory_manager_ar")
    RequirementsDocument.model_validate(doc)
    item = next(e for e in doc["entities"] if e["name"] == "Item")
    category = next(f for f in item["fields"] if f["name"] == "category")
    category["reference_entity"] = "Supplier"
    with pytest.raises(ValidationError, match="unknown entity 'Supplier'"):
        RequirementsDocument.model_validate(doc)


@pytest.mark.parametrize(
    "field",
    [
        {"name": "price", "label": "Price", "type": "decimal", "required": True, "validation": {"min_value": 0}},
        {"name": "sku", "label": "SKU", "type": "string", "required": True, "validation": {"pattern": "^[A-Z]{3}$"}},
        {"name": "day", "label": "Day", "type": "date", "required": False,
         "validation": {"date_constraint": "not_in_past"}},
        {"name": "level", "label": "Level", "type": "enum", "required": True,
         "enum_values": ["a", "b"], "default": "a"},
    ],
)
def test_valid_field_definitions(field):
    EntityField.model_validate(field)


def test_measurable_criterion_accepts_concrete_values():
    AcceptanceCriterion(
        id="AC-1", story_id="US-1", category="create",
        given="the list has 2 records", when="the user saves a record named \"A\"",
        then="the list shows 3 records including \"A\"",
    )
