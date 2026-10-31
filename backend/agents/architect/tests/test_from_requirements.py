import copy

import pytest
from pydantic import ValidationError

from backend.agents.architect import ArchitectureDocument, ArchitectureError, build_architecture
from backend.agents.architect.schema import INPUT_FOR_TYPE

SINGLE_ENTITY = ["task_manager_en", "appointment_booking_en"]


# --- happy path: Ghala's samples -------------------------------------------------------

@pytest.mark.parametrize("name", SINGLE_ENTITY)
def test_sample_produces_valid_architecture(requirements, name):
    req = requirements(name)
    arch = build_architecture(req)
    ArchitectureDocument.model_validate(arch)  # round-trips through the contract

    entity = req["entities"][0]
    assert arch["entity"]["name"] == entity["name"]
    # field names, order, required flags and validation are copied, never renamed
    assert [f["name"] for f in arch["entity"]["fields"]] == [f["name"] for f in entity["fields"]]
    for src, out in zip(entity["fields"], arch["entity"]["fields"]):
        assert out["required"] == src["required"]
        assert out["input"] == INPUT_FOR_TYPE[src["type"]]
        for rule, value in (src["validation"] or {}).items():
            if value is not None:
                assert out["validation"][rule] == value


@pytest.mark.parametrize("name", SINGLE_ENTITY)
def test_list_screen_follows_read_spec(requirements, name):
    read = requirements(name)["entities"][0]["crud"]["read"]
    arch = build_architecture(requirements(name))
    components = {c["type"]: c for c in next(s for s in arch["screens"] if s["id"] == "list")["components"]}
    assert components["table"]["columns"] == read["list_fields"]
    assert components["table"]["sort"] == {"field": read["sort_field"], "direction": read["sort_direction"]}
    assert components["search"]["fields"] == read["search_fields"]
    assert components["filters"]["fields"] == read["filter_fields"]


def test_enum_becomes_select_with_options_and_default(requirements):
    arch = build_architecture(requirements("task_manager_en"))
    status = next(f for f in arch["entity"]["fields"] if f["name"] == "status")
    assert status["input"] == "select"
    assert [o["value"] for o in status["options"]] == ["to_do", "in_progress", "done"]
    assert status["options"][0]["label"] == "To do"
    assert status["default"] == "to_do"


def test_number_fields_get_step(requirements):
    arch = build_architecture(requirements("appointment_booking_en"))
    duration = next(f for f in arch["entity"]["fields"] if f["name"] == "duration_minutes")
    assert duration["input"] == "number" and duration["step"] == 1
    assert duration["validation"] == {"min_value": 15.0, "max_value": 240.0}


def test_storage_and_system_fields(requirements):
    arch = build_architecture(requirements("appointment_booking_en"))
    storage = arch["entity"]["storage"]
    assert storage["key"] == "bunyan_appointment"
    assert storage["system_fields"] == ["id", "created_at", "updated_at"]
    assert not {"id", "created_at", "updated_at"} & {f["name"] for f in arch["entity"]["fields"]}


def test_inline_delete_confirmation_and_messages(requirements):
    arch = build_architecture(requirements("task_manager_en"))
    assert arch["behaviors"]["delete_confirmation"] == "inline"
    assert "{display}" in arch["messages"]["confirm_delete"]
    assert arch["messages"]["empty"] == "No Tasks yet."


def test_arabic_app_is_rtl_and_warns_about_enum_labels(requirements):
    req = requirements("task_manager_en")
    req["language"] = "ar"
    arch = build_architecture(req)
    assert arch["app"]["direction"] == "rtl"
    assert arch["messages"]["required"] == "هذا الحقل مطلوب"
    assert any("Arabic display labels" in w for w in arch["warnings"])


def test_other_category_requirements_are_deferred(requirements):
    req = requirements("appointment_booking_en")
    req["functional_requirements"][5]["category"] = "other"  # FR-6: no double booking
    arch = build_architecture(req)
    assert [r["requirement_id"] for r in arch["deferred_rules"]] == ["FR-6"]


def test_output_is_deterministic(requirements):
    assert build_architecture(requirements("task_manager_en")) == build_architecture(requirements("task_manager_en"))


# --- refusals: things the MVP cannot build ------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("vague_idea_en", "needs_clarification"),
    ("out_of_scope_ar", "rejected_out_of_scope"),
])
def test_only_runs_on_ready_requirements(requirements, name, expected):
    with pytest.raises(ArchitectureError) as exc:
        build_architecture(requirements(name))
    assert expected in exc.value.reasons[0]


def test_multi_entity_with_reference_is_refused_with_reasons(requirements):
    with pytest.raises(ArchitectureError) as exc:
        build_architecture(requirements("inventory_dialect_ar"))
    text = " ".join(exc.value.reasons)
    assert "exactly one entity" in text and "reference" in text


def test_disabled_crud_is_refused(requirements):
    req = requirements("task_manager_en")
    req["entities"][0]["crud"]["delete"]["enabled"] = False
    with pytest.raises(ArchitectureError, match="full CRUD"):
        build_architecture(req)


# --- the contract rejects bad architecture (e.g. from an LLM) ------------------------------

def _arch(requirements):
    return build_architecture(requirements("task_manager_en"))


@pytest.mark.parametrize("mutate,message", [
    (lambda a: a["entity"]["fields"][0].update(input="textarea"), "requires input"),
    (lambda a: a["entity"]["fields"][3].pop("options"), "needs at least two options"),
    (lambda a: a["entity"]["fields"][0].update(name="Title"), "pattern"),
    (lambda a: a["entity"]["fields"].append(dict(a["entity"]["fields"][0], name="id")), "system field"),
    (lambda a: a["screens"][0]["components"][4]["columns"].append("price"), "unknown fields"),
    (lambda a: a["screens"][1]["components"][0]["fields"].pop(), "form must include every field"),
    (lambda a: a["screens"][0]["components"][2].update(fields=["status"]), "search only supports text"),
    (lambda a: a["behaviors"].update(delete_confirmation="browser_dialog"), "delete_confirmation"),
    (lambda a: a["navigation"]["transitions"].pop(), "missing transitions"),
    (lambda a: a["app"].update(direction="rtl"), "direction must be"),
])
def test_contract_rejects(requirements, mutate, message):
    arch = copy.deepcopy(_arch(requirements))
    mutate(arch)
    with pytest.raises(ValidationError, match=message):
        ArchitectureDocument.model_validate(arch)
