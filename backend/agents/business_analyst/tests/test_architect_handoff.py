"""Handoff check: can a downstream consumer (the Software Architect Agent) use the output?

`derive_screens` is a minimal *reference consumer* written only for this test;
it is NOT the Architect Agent. It shows that everything an architecture needs
(storage keys, form inputs, HTML input types, validation attributes, list
columns, search/filter/sort, relations, delete confirmation) can be read from
requirements.json without guessing.
"""

import pytest

from backend.agents.business_analyst.schema import RequirementsDocument

READY_SAMPLES = ["task_manager_en", "inventory_manager_ar", "inventory_dialect_ar", "appointment_booking_en"]

# Mapping documented in contract/INTEGRATION.md.
HTML_INPUT = {
    "string": "text", "text": "textarea", "integer": "number", "decimal": "number", "boolean": "checkbox",
    "date": "date", "time": "time", "datetime": "datetime-local", "email": "email", "phone": "tel",
    "url": "url", "enum": "select", "reference": "select",
}


def derive_screens(doc: RequirementsDocument) -> dict:
    screens = {}
    for entity in doc.entities:
        inputs = []
        for f in entity.fields:
            attrs = {"required": f.required}
            v = f.validation
            if v.min_length is not None:
                attrs["minlength"] = v.min_length
            if v.max_length is not None:
                attrs["maxlength"] = v.max_length
            if v.min_value is not None:
                attrs["min"] = v.min_value
            if v.max_value is not None:
                attrs["max"] = v.max_value
            if v.pattern:
                attrs["pattern"] = v.pattern
            if f.type == "decimal":
                attrs["step"] = "0.01"
            options = f.enum_values if f.type == "enum" else None
            if f.type == "reference":
                target = doc.entity(f.reference_entity)
                options = f"records of {target.name}, labelled by {target.display_field}"
            inputs.append({"name": f.name, "label": f.label, "input": HTML_INPUT[f.type],
                           "attrs": attrs, "options": options})
        read = entity.crud.read
        screens[entity.name] = {
            "storage_key": f"bunyan.{entity.name.lower()}",
            "form": inputs,
            "list_columns": read.list_fields or [entity.display_field],
            "search": read.search_fields, "filters": read.filter_fields,
            "sort": (read.sort_field, read.sort_direction),
            "operations": entity.crud.enabled_operations(),
            "confirm_delete": entity.crud.delete.requires_confirmation,
            "rtl": doc.language == "ar",
        }
    return screens


@pytest.mark.parametrize("name", READY_SAMPLES)
def test_reference_consumer_can_derive_every_screen(sample_output, name):
    doc = RequirementsDocument.model_validate(sample_output(name))
    assert doc.status == "ready_for_review"
    screens = derive_screens(doc)
    assert set(screens) == {e.name for e in doc.entities}
    for entity in doc.entities:
        screen = screens[entity.name]
        assert screen["operations"] == ["create", "read", "update", "delete"]
        assert len(screen["form"]) == len(entity.fields)
        assert all(i["input"] for i in screen["form"])
        assert screen["list_columns"]
        for f in entity.fields:
            if f.type in ("enum", "reference"):
                assert next(i for i in screen["form"] if i["name"] == f.name)["options"]


@pytest.mark.parametrize("name", READY_SAMPLES)
def test_every_criterion_is_traceable_to_an_entity_operation(sample_output, name):
    """QA and the Architect can map each acceptance criterion to a screen and an operation."""
    doc = RequirementsDocument.model_validate(sample_output(name))
    stories = {s.id: s for s in doc.user_stories}
    for ac in doc.acceptance_criteria:
        story = stories[ac.story_id]
        assert story.entity in {e.name for e in doc.entities}
        assert story.operation in {"create", "read", "update", "delete"}


def test_arabic_output_keeps_english_identifiers(sample_output):
    doc = RequirementsDocument.model_validate(sample_output("inventory_dialect_ar"))
    assert doc.language == "ar" and derive_screens(doc)["Item"]["rtl"]
    for entity in doc.entities:
        assert entity.name.isascii()
        assert all(f.name.isascii() for f in entity.fields)
        assert not entity.label.isascii()  # display labels are Arabic
