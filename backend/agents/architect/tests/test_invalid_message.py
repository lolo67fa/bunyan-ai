"""fields[].messages.invalid (v0.3.2): optional, number and select fields only, backwards compatible."""

import copy

import pytest
from pydantic import ValidationError

from backend.agents.architect import build_architecture
from backend.agents.architect.schema import ArchitectureDocument


def _doc(requirements):
    return build_architecture(requirements("scenario_b_inventory_ar"))


def test_documents_without_invalid_stay_valid(requirements):
    for name in ("task_manager_en", "scenario_b_inventory_ar", "appointment_booking_en"):
        arch = build_architecture(requirements(name))
        ArchitectureDocument.model_validate(arch)
        assert all("invalid" not in f["messages"] for f in arch["entity"]["fields"])  # nothing new by default


def test_invalid_is_accepted_on_number_and_enum_fields(requirements):
    arch = _doc(requirements)
    for f in arch["entity"]["fields"]:
        if f["type"] in ("integer", "decimal", "enum"):
            f["messages"]["invalid"] = "قيمة غير صحيحة"
    ArchitectureDocument.model_validate(arch)


def test_invalid_is_refused_on_text_fields(requirements):
    arch = copy.deepcopy(_doc(requirements))
    text = next(f for f in arch["entity"]["fields"] if f["type"] in ("string", "text"))
    text["messages"]["invalid"] = "x"
    with pytest.raises(ValidationError, match="only allowed on number and enum fields"):
        ArchitectureDocument.model_validate(arch)


def test_english_whole_number_criterion(requirements):
    req = requirements("scenario_b_inventory_ar")
    qty = next(f for f in req["entities"][0]["fields"] if f["type"] == "integer")
    req["acceptance_criteria"].append({
        "id": "AC-99", "category": "validation", "story_id": req["acceptance_criteria"][0].get("story_id"),
        "given": "the form is open", "when": f'the user enters 2.5 in "{qty["label"]}" and clicks "حفظ"',
        "then": f'the message "{qty["label"]} must be a whole number" appears next to "{qty["label"]}"',
    })
    arch = build_architecture(req)
    field = next(f for f in arch["entity"]["fields"] if f["name"] == qty["name"])
    assert field["messages"]["invalid"] == f'{qty["label"]} must be a whole number'
