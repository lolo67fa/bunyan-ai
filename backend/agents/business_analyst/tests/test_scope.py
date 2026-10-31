"""CRUD scope enforcement: out-of-scope features are flagged and never become requirements."""

import pytest
from pydantic import ValidationError

from backend.agents.business_analyst import analyze
from backend.agents.business_analyst.analyst import OutputRejected, finalize
from backend.agents.business_analyst.schema import OutOfScopeItem, RequirementsDocument
from backend.agents.business_analyst.scope import detect_out_of_scope, find_scope_violations


@pytest.mark.parametrize(
    "text, category",
    [
        ("Users must log in with a password", "authentication"),
        ("Customers pay online with a credit card", "payments"),
        ("It should be an iOS app", "native_mobile"),
        ("Share the list with my team in real-time", "realtime_collaboration"),
        ("Send SMS reminders to clients", "external_integration"),
        ("Store everything in a MySQL database", "server_backend"),
        ("A full ERP for the company", "enterprise_system"),
        ("Let users upload photos of products", "file_storage"),
        ("أريد تسجيل الدخول بكلمة مرور", "authentication"),
        ("مع بوابة دفع للبطاقات", "payments"),
        ("تطبيق جوال للأندرويد", "native_mobile"),
        ("إرسال رسائل نصية للعملاء", "external_integration"),
        ("رفع صور المنتجات", "file_storage"),
    ],
)
def test_guard_detects_out_of_scope_features(text, category):
    lang = "ar" if any("؀" <= c <= "ۿ" for c in text) else "en"
    assert category in {i.category for i in detect_out_of_scope(text, lang)}


@pytest.mark.parametrize(
    "text",
    [
        "A task manager with title, due date and status",
        "Track whether each order is paid or unpaid",          # payment *status* is CRUD data
        "Library app to record book checkouts and returns",   # 'checkout' of a book is CRUD data
        "The list updates in real time after the user clicks Save",
        "تطبيق لإدارة المواعيد مع التاريخ والوقت",
        "تسجيل مدى توفر المنتج",                               # 'مدى' (range) is not the mada payment network
    ],
)
def test_guard_does_not_flag_plain_crud_ideas(text):
    lang = "ar" if any("؀" <= c <= "ۿ" for c in text) else "en"
    assert detect_out_of_scope(text, lang) == []


def test_mixed_idea_keeps_crud_core_and_flags_extras(sample_input):
    doc = analyze(sample_input("appointment_booking_en")["idea"], mode="mock")
    assert doc.status == "ready_for_review"
    assert [e.name for e in doc.entities] == ["Appointment"]
    flagged = {i.category: i for i in doc.out_of_scope}
    assert "external_integration" in flagged
    assert flagged["external_integration"].action == "replaced_with_crud_alternative"
    assert find_scope_violations(doc) == []


def test_arabic_login_request_is_excluded(sample_input):
    doc = analyze(sample_input("inventory_manager_ar")["idea"], mode="mock")
    assert doc.status == "ready_for_review"
    assert "authentication" in {i.category for i in doc.out_of_scope}
    field_names = {f.name for e in doc.entities for f in e.fields}
    assert not field_names & {"password", "password_hash", "username"}


def test_fully_out_of_scope_idea_is_rejected(sample_input):
    doc = analyze(sample_input("out_of_scope_ar")["idea"], mode="mock")
    assert doc.status == "rejected_out_of_scope"
    assert {"payments", "native_mobile", "realtime_collaboration"} <= {i.category for i in doc.out_of_scope}
    assert doc.entities == [] and doc.functional_requirements == []


def test_scope_violation_inside_requirements_is_detected(task_doc):
    task_doc["functional_requirements"][0]["description"] = (
        "The system shall let the user pay online with a credit card when creating a Task."
    )
    doc = RequirementsDocument.model_validate(task_doc)
    violations = find_scope_violations(doc)
    assert [(v.location, v.category) for v in violations] == [("FR-1", "payments")]


def test_password_field_is_a_scope_violation(task_doc):
    task_doc["entities"][0]["fields"].append(
        {"name": "password", "label": "Password", "type": "string", "required": True}
    )
    doc = RequirementsDocument.model_validate(task_doc)
    assert ("Task.password", "authentication") in {(v.location, v.category) for v in find_scope_violations(doc)}


def test_finalize_rejects_llm_output_with_out_of_scope_requirement(task_doc):
    import json

    task_doc["user_stories"][0]["goal"] = "log in with my password before adding a Task"
    with pytest.raises(OutputRejected) as exc:
        finalize(json.dumps(task_doc), task_doc["source_idea"], "en")
    assert any("authentication" in e for e in exc.value.errors)


def test_finalize_adds_flags_the_llm_forgot(task_doc):
    import json

    idea = task_doc["source_idea"] + " Also let me pay online for premium features."
    doc = finalize(json.dumps(task_doc), idea, "en")
    assert "payments" in {i.category for i in doc.out_of_scope}


def test_rejected_status_requires_out_of_scope_items(task_doc):
    task_doc["status"] = "rejected_out_of_scope"
    task_doc["out_of_scope"] = []
    with pytest.raises(ValidationError, match="out_of_scope item"):
        RequirementsDocument.model_validate(task_doc)


def test_crud_alternative_needs_description():
    with pytest.raises(ValidationError):
        OutOfScopeItem(feature="Online payments", category="payments",
                       reason="Not in the MVP.", action="replaced_with_crud_alternative")
