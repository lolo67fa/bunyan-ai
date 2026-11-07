import copy

import pytest
from pydantic import ValidationError

from backend.agents.architect import ArchitectureDocument, ArchitectureError, build_architecture
from backend.agents.architect.schema import INPUT_FOR_TYPE

# Every Business Analyst sample on main that is ready_for_review with one entity.
SINGLE_ENTITY = [
    "task_manager_en",
    "appointment_booking_en",
    "inventory_dialect_ar",
    "scenario_a_task_en",
    "scenario_b_inventory_ar",
    "scenario_c_booking_ar",
]


def _field(arch, name):
    return next(f for f in arch["entity"]["fields"] if f["name"] == name)


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
    if read.get("sort_field"):
        assert components["table"]["sort"] == {"field": read["sort_field"], "direction": read["sort_direction"]}
    if read.get("search_fields"):
        assert components["search"]["fields"] == read["search_fields"]


def test_enum_becomes_select_with_options_and_default(requirements):
    arch = build_architecture(requirements("task_manager_en"))
    status = _field(arch, "status")
    assert status["input"] == "select"
    assert [o["value"] for o in status["options"]] == ["to_do", "in_progress", "done"]
    assert status["options"][0]["label"] == "To do"
    assert status["default"] == "to_do"
    assert "empty_option" not in status  # has a default, so it never starts empty


def test_arabic_enum_values_are_their_own_labels(requirements):
    arch = build_architecture(requirements("scenario_c_booking_ar"))
    status = _field(arch, "status")
    assert [o["label"] for o in status["options"]] == ["مؤكد", "ملغى"]
    assert arch["warnings"] == []


def test_required_select_without_default_starts_empty(requirements):
    # Sara's open point: Service in the appointment sample is required and has no default
    service = _field(build_architecture(requirements("appointment_booking_en")), "service")
    assert service["required"] and "default" not in service
    assert service["empty_option"] == "Select Service"
    assert service["messages"]["required"] == "Service is required"


def test_number_fields_get_step_and_display_format(requirements):
    arch = build_architecture(requirements("scenario_b_inventory_ar"))
    assert _field(arch, "price")["display_format"] == {"decimals": 2}
    assert _field(arch, "price")["step"] == 0.01
    assert _field(arch, "quantity")["display_format"] == {"decimals": 0}
    duration = _field(build_architecture(requirements("appointment_booking_en")), "duration_minutes")
    assert duration["validation"] == {"min_value": 15.0, "max_value": 240.0}


def test_every_field_rule_has_its_own_message(requirements):
    arch = build_architecture(requirements("appointment_booking_en"))
    assert _field(arch, "client_name")["messages"] == {
        "required": "Client name is required",
        "min_length": "Client name must be at least 2 characters",
        "max_length": "Client name must be at most 100 characters",
    }
    assert _field(arch, "date")["messages"]["date_constraint"] == "Date cannot be in the past"
    assert _field(arch, "notes")["messages"] == {"max_length": "Notes must be at most 500 characters"}


def test_arabic_field_messages(requirements):
    arch = build_architecture(requirements("scenario_b_inventory_ar"))
    assert _field(arch, "quantity")["messages"] == {
        "required": "الكمية: هذا الحقل مطلوب",
        "min_value": "الكمية: أقل قيمة مسموحة 0",
    }


def test_storage_and_system_fields(requirements):
    arch = build_architecture(requirements("appointment_booking_en"))
    storage = arch["entity"]["storage"]
    assert storage["key"] == "bunyan_appointment"
    assert storage["system_fields"] == ["id", "created_at", "updated_at"]
    assert not {"id", "created_at", "updated_at"} & {f["name"] for f in arch["entity"]["fields"]}


def test_screen_messages_include_empty_and_no_results(requirements):
    arch = build_architecture(requirements("task_manager_en"))
    assert arch["behaviors"]["delete_confirmation"] == "inline"
    assert "{display}" in arch["messages"]["confirm_delete"]
    assert arch["messages"]["empty"] == "No records yet."
    assert arch["messages"]["no_results"] == "No records match your search."
    ar = build_architecture(requirements("scenario_c_booking_ar"))["messages"]
    assert ar["empty"] == "لا توجد سجلات بعد." and ar["no_results"] == "لا توجد نتائج مطابقة للبحث."


def test_arabic_app_is_rtl_and_warns_about_english_enum_labels(requirements):
    req = requirements("task_manager_en")
    req["language"] = "ar"
    arch = build_architecture(req)
    assert arch["app"]["direction"] == "rtl"
    assert _field(arch, "title")["messages"]["required"] == "Title: هذا الحقل مطلوب"
    assert any("Arabic display labels" in w for w in arch["warnings"])


def test_other_category_requirements_are_deferred(requirements):
    req = requirements("appointment_booking_en")
    req["functional_requirements"][5]["category"] = "other"  # FR-6: no double booking
    arch = build_architecture(req)
    assert [r["requirement_id"] for r in arch["deferred_rules"]] == ["FR-6"]


def test_output_is_deterministic(requirements):
    assert build_architecture(requirements("task_manager_en")) == build_architecture(requirements("task_manager_en"))


# --- rule M1: texts quoted in acceptance criteria are used verbatim -------------------------

def _ac(req, ac_id):
    return next(a for a in req["acceptance_criteria"] if a["id"] == ac_id)


def test_button_labels_come_from_acceptance_criteria(requirements):
    for name, save, delete in [("task_manager_en", "Save", "Delete"), ("scenario_b_inventory_ar", "حفظ", "حذف")]:
        arch = build_architecture(requirements(name))
        paths = {v["path"]: v["text"] for v in arch["verbatim_messages"]}
        assert paths["screens.form.save_button"] == save
        assert paths["messages.delete_button"] == delete


def test_quoted_field_message_is_used_verbatim(requirements):
    req = requirements("task_manager_en")
    _ac(req, "AC-3")["then"] = 'the Task is not saved and the message "Title needs 3+ letters" is shown next to "Title"'
    _ac(req, "AC-2")["then"] = 'no Task is saved and the message "Please enter a title" is shown next to "Title"'
    arch = build_architecture(req)
    title = _field(arch, "title")["messages"]
    assert title["min_length"] == "Title needs 3+ letters"   # AC-3: 2 characters < min_length 3
    assert title["required"] == "Please enter a title"       # AC-2: fields left empty
    assert title["max_length"] == "Title must be at most 100 characters"  # not quoted -> template
    sources = {v["path"]: v["source"] for v in arch["verbatim_messages"]}
    assert sources["entity.fields.title.messages.min_length"] == "AC-3"
    assert sources["entity.fields.title.messages.required"] == "AC-2"


def test_quoted_screen_messages_are_used_verbatim(requirements):
    req = requirements("scenario_b_inventory_ar")
    _ac(req, "AC-8")["then"] = 'تظهر رسالة "لا توجد منتجات، أضف أول منتج" بدلاً من القائمة'
    _ac(req, "AC-9")["when"] = 'يكتب المستخدم "غير موجود" في مربع البحث'
    _ac(req, "AC-9")["then"] = 'تظهر رسالة "ما فيه نتائج" بدلاً من القائمة'
    _ac(req, "AC-12")["then"] = 'تظهر رسالة التأكيد "متأكد تبي تحذف المنتج؟" ثم يُزال من القائمة'
    msgs = build_architecture(req)["messages"]
    assert msgs["empty"] == "لا توجد منتجات، أضف أول منتج"
    assert msgs["no_results"] == "ما فيه نتائج"
    assert msgs["confirm_delete"] == "متأكد تبي تحذف المنتج؟"


def test_confirm_button_label_from_acceptance_criteria(requirements):
    req = requirements("task_manager_en")
    _ac(req, "AC-12")["when"] = 'the user clicks "Delete" on it and confirms by clicking "Yes, delete"'
    arch = build_architecture(req)
    assert arch["messages"]["confirm_button"] == "Yes, delete"


def test_business_rule_message_is_not_attached_to_a_field(requirements):
    # AC-8 "This time slot is already booked" is about two records, not about the Date field
    arch = build_architecture(requirements("appointment_booking_en"))
    assert _field(arch, "date")["messages"]["date_constraint"] == "Date cannot be in the past"
    assert any("AC-8" in w and "business rule" in w for w in arch["warnings"])


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
        build_architecture(requirements("inventory_manager_ar"))
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
    (lambda a: a["entity"]["fields"][0]["messages"].pop("min_length"), "missing messages"),
    (lambda a: a["entity"]["fields"][0]["messages"].update(pattern="x"), "rules it does not have"),
    (lambda a: a["entity"]["fields"][3].update(empty_option="Select"), "must not have empty_option"),
    (lambda a: a["screens"][0]["components"][4]["columns"].append("price"), "unknown fields"),
    (lambda a: a["screens"][1]["components"][0]["fields"].pop(), "form must include every field"),
    (lambda a: a["screens"][0]["components"][2].update(fields=["status"]), "search only supports text"),
    (lambda a: a["behaviors"].update(delete_confirmation="browser_dialog"), "delete_confirmation"),
    (lambda a: a["navigation"]["transitions"].pop(), "missing transitions"),
    (lambda a: a["app"].update(direction="rtl"), "direction must be"),
    (lambda a: a["messages"].update(delete_button="Remove"), "is not used at"),
])
def test_contract_rejects(requirements, mutate, message):
    arch = copy.deepcopy(_arch(requirements))
    mutate(arch)
    with pytest.raises(ValidationError, match=message):
        ArchitectureDocument.model_validate(arch)


def test_contract_requires_decimals_for_numbers(requirements):
    arch = copy.deepcopy(build_architecture(requirements("scenario_b_inventory_ar")))
    next(f for f in arch["entity"]["fields"] if f["name"] == "price").pop("display_format")
    with pytest.raises(ValidationError, match="display_format.decimals"):
        ArchitectureDocument.model_validate(arch)
