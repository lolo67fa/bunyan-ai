"""Deterministic mapping: approved requirements.json -> architecture.json.

This is the backbone of the Architect Agent. Everything that has exactly one right
answer (control types, storage key, screens, navigation, validation) is derived here
in code, so it is identical on every run and cannot be hallucinated. A model is only
needed for the parts marked ``warnings`` (e.g. human labels for enum values), which
can be layered on top later without changing this contract.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .schema import (
    INPUT_FOR_TYPE,
    NUMBER_TYPES,
    SEARCHABLE_TYPES,
    FILTERABLE_TYPES,
    ArchitectureDocument,
)

_TEXT = {
    "ar": {
        "add": "إضافة {label}", "save": "حفظ", "cancel": "إلغاء", "search": "بحث في {plural}",
        "form_title": "بيانات {label}", "edit": "تعديل", "delete": "حذف",
        "confirm": "تأكيد الحذف", "cancel_delete": "تراجع",
        "empty": "لا توجد {plural} بعد.", "required": "هذا الحقل مطلوب", "invalid": "القيمة غير صحيحة",
        "unique": "هذه القيمة مستخدمة مسبقًا", "created": "تمت الإضافة بنجاح", "updated": "تم حفظ التعديلات",
        "deleted": "تم الحذف", "confirm_delete": "هل تريد حذف «{display}»؟",
    },
    "en": {
        "add": "Add {label}", "save": "Save", "cancel": "Cancel", "search": "Search {plural}",
        "form_title": "{label} details", "edit": "Edit", "delete": "Delete",
        "confirm": "Confirm delete", "cancel_delete": "Keep",
        "empty": "No {plural} yet.", "required": "This field is required", "invalid": "Invalid value",
        "unique": "This value is already in use", "created": "Added successfully", "updated": "Changes saved",
        "deleted": "Deleted", "confirm_delete": "Delete “{display}”?",
    },
}


class ArchitectureError(ValueError):
    """The requirements cannot be turned into an MVP architecture. ``reasons`` explains why."""

    def __init__(self, reasons: List[str]):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def humanize(value: str) -> str:
    text = value.replace("_", " ").replace("-", " ").strip()
    return text[:1].upper() + text[1:]


def _check_input(req: Dict[str, Any]) -> List[str]:
    reasons = []
    if req.get("schema_version") != "0.1.0-proposal":
        reasons.append(f"unsupported requirements schema_version {req.get('schema_version')!r}")
    if req.get("status") != "ready_for_review":
        reasons.append(f"requirements status is {req.get('status')!r}; the Architect runs only on 'ready_for_review' after user approval")
        return reasons
    entities = req.get("entities") or []
    if len(entities) != 1:
        reasons.append(f"MVP supports exactly one entity, got {len(entities)}: {[e['name'] for e in entities]}")
    for e in entities:
        refs = [f["name"] for f in e["fields"] if f["type"] == "reference"]
        if refs:
            reasons.append(f"entity '{e['name']}' has reference fields {refs}; relations are out of MVP scope")
        disabled = [op for op in ("create", "read", "update", "delete") if not e["crud"][op]["enabled"]]
        if disabled:
            reasons.append(f"entity '{e['name']}' disables {disabled}; the MVP template always has full CRUD")
        if len(e["fields"]) > 12:
            reasons.append(f"entity '{e['name']}' has {len(e['fields'])} fields; MVP maximum is 12")
    return reasons


def _field(f: Dict[str, Any], list_fields: List[str], language: str, warnings: List[str]) -> Dict[str, Any]:
    v = {k: val for k, val in (f.get("validation") or {}).items() if val is not None}
    out: Dict[str, Any] = {
        "name": f["name"],
        "label": f["label"],
        "type": f["type"],
        "input": INPUT_FOR_TYPE[f["type"]],
        "required": f["required"],
        "unique": f.get("unique", False),
        "show_in_list": f["name"] in list_fields,
        "validation": v,
    }
    if f.get("default") is not None:
        out["default"] = f["default"]
    if f["type"] in NUMBER_TYPES:
        out["step"] = 1 if f["type"] == "integer" else 0.01
    if f["type"] == "enum":
        out["options"] = [{"value": val, "label": humanize(val)} for val in f["enum_values"]]
        if language == "ar":
            warnings.append(
                f"enum labels for '{f['name']}' were generated from English values {f['enum_values']}; "
                "requirements.json should provide Arabic display labels"
            )
    return out


def build_architecture(req: Dict[str, Any]) -> Dict[str, Any]:
    """Return a validated architecture.json dict, or raise ArchitectureError."""
    reasons = _check_input(req)
    if reasons:
        raise ArchitectureError(reasons)

    language = req["language"]
    t = _TEXT[language]
    e = req["entities"][0]
    read = e["crud"]["read"]
    list_fields = read.get("list_fields") or [e["display_field"]]
    warnings: List[str] = []
    fields = [_field(f, list_fields, language, warnings) for f in e["fields"]]
    by_name = {f["name"]: f for f in fields}
    fmt = {"label": e["label"], "plural": e["plural_label"]}

    list_components: List[Dict[str, Any]] = [{"type": "header"}, {"type": "add_button", "label": t["add"].format(**fmt)}]
    search = [n for n in read.get("search_fields", []) if by_name[n]["type"] in SEARCHABLE_TYPES]
    dropped = set(read.get("search_fields", [])) - set(search)
    if dropped:
        warnings.append(f"search_fields {sorted(dropped)} are not text fields and were left out of search")
    if search:
        list_components.append({"type": "search", "fields": search, "placeholder": t["search"].format(**fmt)})
    filters = [n for n in read.get("filter_fields", []) if by_name[n]["type"] in FILTERABLE_TYPES]
    dropped = set(read.get("filter_fields", [])) - set(filters)
    if dropped:
        warnings.append(f"filter_fields {sorted(dropped)} are not enum/boolean/date fields and were left out of filters")
    if filters:
        list_components.append({"type": "filters", "fields": filters})
    table: Dict[str, Any] = {"type": "table", "columns": list_fields, "row_actions": ["edit", "delete"]}
    if read.get("sort_field"):
        table["sort"] = {"field": read["sort_field"], "direction": read.get("sort_direction", "asc")}
    list_components += [table, {"type": "empty_state"}]

    deferred = [
        {"requirement_id": r["id"], "description": r["description"]}
        for r in req.get("functional_requirements", [])
        if r["category"] == "other"
    ]

    doc = {
        "app": {
            "name": req["app"]["name"],
            "description": req["app"].get("description", ""),
            "language": language,
            "direction": "rtl" if language == "ar" else "ltr",
        },
        "entity": {
            "name": e["name"],
            "label": e["label"],
            "plural_label": e["plural_label"],
            "display_field": e["display_field"],
            "storage": {"key": f"bunyan_{snake(e['name'])}"},
            "fields": fields,
        },
        "screens": [
            {"id": "list", "type": "list", "title": e["plural_label"], "components": list_components},
            {
                "id": "form", "type": "form", "title": t["form_title"].format(**fmt), "modes": ["create", "edit"],
                "components": [
                    {"type": "form_fields", "fields": [f["name"] for f in fields]},
                    {"type": "save_button", "label": t["save"]},
                    {"type": "cancel_button", "label": t["cancel"]},
                ],
            },
        ],
        "navigation": {
            "initial_screen": "list",
            "transitions": [
                {"from": "list", "event": "add", "to": "form", "mode": "create"},
                {"from": "list", "event": "edit", "to": "form", "mode": "edit"},
                {"from": "form", "event": "save_success", "to": "list"},
                {"from": "form", "event": "cancel", "to": "list"},
            ],
        },
        "behaviors": {
            "check_unique_before_save": any(f["unique"] for f in fields),
            "delete_confirmation": "inline" if e["crud"]["delete"].get("requires_confirmation", True) else "none",
        },
        "messages": {
            "empty": t["empty"].format(**fmt), "required": t["required"], "invalid": t["invalid"],
            "unique": t["unique"], "created": t["created"], "updated": t["updated"], "deleted": t["deleted"],
            "confirm_delete": t["confirm_delete"], "confirm_button": t["confirm"],
            "cancel_delete_button": t["cancel_delete"], "edit_button": t["edit"], "delete_button": t["delete"],
        },
        "deferred_rules": deferred,
        "warnings": warnings,
    }
    # Validation is the contract: if this raises, the mapping above has a bug.
    return ArchitectureDocument.model_validate(doc).model_dump(mode="json", by_alias=True, exclude_none=True)
