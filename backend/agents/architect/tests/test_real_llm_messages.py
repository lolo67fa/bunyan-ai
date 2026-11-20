"""Validation messages from a real LLM Business Analyst run reach the right field rules.

The model writes field names without quotes ("بجانب حقل الكمية"), one "required" criterion for
several fields, and one message for a length range. None of these may be silently dropped.
"""

from backend.agents.architect import build_architecture
from backend.agents.architect.schema import ArchitectureDocument


def fields(arch):
    return {f["name"]: f["messages"] for f in arch["entity"]["fields"]}


def test_real_llm_validation_messages_are_mapped(requirements):
    arch = build_architecture(requirements("real_llm_inventory_ar"))
    ArchitectureDocument.model_validate(arch)  # the contract still holds
    m = fields(arch)
    for name in ("name", "quantity", "price"):  # AC-2: one message next to each of the three fields
        assert m[name]["required"] == "هذا الحقل مطلوب"
    assert m["name"]["min_length"] == m["name"]["max_length"] == "يجب أن يتكون اسم المنتج من 2 إلى 100 حرف"  # AC-3/4
    assert m["quantity"]["min_value"] == "يجب أن تكون الكمية 0 أو أكثر"  # AC-5, AC-16
    assert m["price"]["min_value"] == "يجب أن يكون السعر 0 أو أكثر"  # AC-7
    sources = {v["path"]: v["source"] for v in arch["verbatim_messages"]}
    assert sources["entity.fields.price.messages.required"] == "AC-2"
    assert sources["entity.fields.name.messages.min_length"] == "AC-3"


def test_the_unsupported_whole_number_message_is_reported_not_dropped(requirements):
    warnings = build_architecture(requirements("real_llm_inventory_ar"))["warnings"]
    not_tied = [w for w in warnings if "not tied to one field rule" in w]
    assert not_tied == []  # was 7 before the fix
    whole = [w for w in warnings if w.startswith("AC-6 ")]
    assert len(whole) == 1 and "يجب أن تكون الكمية عدداً صحيحاً" in whole[0] and "no message slot" in whole[0]


def test_an_unquoted_word_in_a_sentence_still_does_not_name_a_field(requirements):
    # "for the same date" is a business rule, not the Date field: only "the field X" / "X field" count
    arch = build_architecture(requirements("appointment_booking_en"))
    assert any("AC-8" in w and "business rule" in w for w in arch["warnings"])


def test_english_field_wording(requirements):
    req = requirements("task_manager_en")
    ac = next(a for a in req["acceptance_criteria"] if a["id"] == "AC-3")
    ac["then"] = 'the message "Title must have 3 to 100 letters" appears next to the Title field'
    m = fields(build_architecture(req))
    assert m["title"]["min_length"] == m["title"]["max_length"] == "Title must have 3 to 100 letters"


def test_the_template_falls_back_to_the_app_language_for_number_errors():
    from pathlib import Path

    js = (Path(__file__).resolve().parents[4] / "templates" / "crud" / "app.js").read_text(encoding="utf-8")
    assert "m.invalid||messages.invalid||'Invalid number'" in js
