"""Deterministic mapping: approved requirements.json -> architecture.json.

This is the backbone of the Architect Agent. Everything that has exactly one right
answer (control types, storage key, screens, navigation, validation, messages) is derived
here in code, so it is identical on every run and cannot be hallucinated. A model is only
needed for the parts marked ``warnings`` (e.g. human labels for English enum values),
which can be layered on top later without changing this contract.

Messages follow rule M1 (CONTRACT.md §6):
- a message the acceptance criteria quote literally is copied verbatim and listed in
  ``verbatim_messages`` so QA can compare it exactly;
- every other message is generated from one fixed template per rule, so wording is the
  same in every app and QA only checks that the message is visible.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from .schema import (
    FILTERABLE_TYPES,
    INPUT_FOR_TYPE,
    NUMBER_TYPES,
    SEARCHABLE_TYPES,
    ArchitectureDocument,
)

_TEXT = {
    "ar": {
        "add": "إضافة {label}", "save": "حفظ", "cancel": "إلغاء", "search": "بحث في {plural}",
        "form_title": "بيانات {label}", "edit": "تعديل", "delete": "حذف",
        "confirm": "تأكيد الحذف", "cancel_delete": "تراجع",
        "empty": "لا توجد سجلات بعد.", "no_results": "لا توجد نتائج مطابقة للبحث.",
        "invalid": "القيمة غير صحيحة",
        "created": "تمت الإضافة بنجاح", "updated": "تم حفظ التعديلات", "deleted": "تم الحذف",
        "confirm_delete": "هل تريد حذف «{display}»؟",
        "empty_option": "اختر {label}",
        # field rules: "label: rule" keeps Arabic grammar right for any label (no gender/definiteness agreement)
        "required": "{label}: هذا الحقل مطلوب",
        "unique": "{label}: هذه القيمة مستخدمة مسبقًا",
        "min_length": "{label}: يجب إدخال {n} أحرف على الأقل",
        "max_length": "{label}: الحد الأقصى {n} حرفًا",
        "min_value": "{label}: أقل قيمة مسموحة {n}",
        "max_value": "{label}: أعلى قيمة مسموحة {n}",
        "pattern": "{label}: الصيغة غير صحيحة",
        "not_in_past": "{label}: لا يمكن اختيار تاريخ سابق",
        "not_in_future": "{label}: لا يمكن اختيار تاريخ لاحق",
    },
    "en": {
        "add": "Add {label}", "save": "Save", "cancel": "Cancel", "search": "Search {plural}",
        "form_title": "{label} details", "edit": "Edit", "delete": "Delete",
        "confirm": "Confirm delete", "cancel_delete": "Keep",
        "empty": "No records yet.", "no_results": "No records match your search.",
        "invalid": "Invalid value",
        "created": "Added successfully", "updated": "Changes saved", "deleted": "Deleted",
        "confirm_delete": "Delete “{display}”?",
        "empty_option": "Select {label}",
        "required": "{label} is required",
        "unique": "{label} is already in use",
        "min_length": "{label} must be at least {n} characters",
        "max_length": "{label} must be at most {n} characters",
        "min_value": "{label} must be {n} or more",
        "max_value": "{label} must be {n} or less",
        "pattern": "{label} format is invalid",
        "not_in_past": "{label} cannot be in the past",
        "not_in_future": "{label} cannot be in the future",
    },
}

# --- acceptance-criteria text patterns (EN + AR) -----------------------------------------------
_QUOTE = r"[\"“«]([^\"”»]+)[\"”»]"
# a quoted text introduced as a message: message "X", the text "X", رسالة "X", نص "X"
# (one optional word in between: رسالة التأكيد "X", the error message "X")
_MESSAGE_RE = re.compile(
    r"(?:message|text|reads|رسالة|الرسالة|النص|نص|عبارة)(?:\s+[^\s\"“«]+)?\s*[:：]?\s*" + _QUOTE,
    re.IGNORECASE,
)
# a quoted button: clicks "X", presses "X", يضغط "X", ينقر "X"
# Arabic puts the subject between verb and object (يضغط المستخدم "حذف"), so allow up to two words.
_CLICK_RE = re.compile(
    r"(?:click(?:s|ing)?(?:\s+on)?|press(?:es)?|taps?|(?:يضغط|ينقر|يختار)(?:\s+[^\s\"“«]+){0,2})\s+" + _QUOTE,
    re.IGNORECASE,
)
_EMPTY_WORDS = re.compile(r"\b(empty|leaves?|clears?|blank|without)\b|فارغ|يترك|يمسح|بدون|دون", re.IGNORECASE)
_NO_RECORDS = re.compile(r"no (records|items|\w+ yet)|empty[- ]state|لا توجد|عدم وجود|فارغة", re.IGNORECASE)
_SEARCH = re.compile(r"search|filter|بحث|تصفية|فلتر", re.IGNORECASE)
_CONFIRM = re.compile(r"confirm|تأكيد|يؤكد", re.IGNORECASE)


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


def _num(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


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


def _field_messages(f: Dict[str, Any], v: Dict[str, Any], t: Dict[str, str]) -> Dict[str, str]:
    label = f["label"]
    out: Dict[str, str] = {}
    if f["required"]:
        out["required"] = t["required"].format(label=label)
    if f.get("unique"):
        out["unique"] = t["unique"].format(label=label)
    for rule in ("min_length", "max_length", "min_value", "max_value"):
        if rule in v:
            out[rule] = t[rule].format(label=label, n=_num(v[rule]))
    if "pattern" in v:
        out["pattern"] = t["pattern"].format(label=label)
    if "date_constraint" in v:
        out["date_constraint"] = t[v["date_constraint"]].format(label=label)
    return out


def _field(f: Dict[str, Any], list_fields: List[str], language: str, t: Dict[str, str], warnings: List[str]) -> Dict[str, Any]:
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
        "messages": _field_messages(f, v, t),
    }
    if f.get("default") is not None:
        out["default"] = f["default"]
    if f["type"] in NUMBER_TYPES:
        decimals = 0 if f["type"] == "integer" else 2
        out["step"] = 1 if decimals == 0 else 0.01
        out["display_format"] = {"decimals": decimals}
    if f["type"] == "enum":
        ascii_values = [val for val in f["enum_values"] if val.isascii()]
        out["options"] = [
            {"value": val, "label": humanize(val) if val.isascii() else val} for val in f["enum_values"]
        ]
        if f.get("default") is None:
            out["empty_option"] = t["empty_option"].format(label=f["label"])
        if language == "ar" and ascii_values:
            warnings.append(
                f"enum labels for '{f['name']}' were generated from English values {ascii_values}; "
                "requirements.json should provide Arabic display labels"
            )
    return out


def _label_in(text: str, fields: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The field whose label the text quotes ("Client name" / «اسم العميل»). Unquoted words never count,
    so a business rule like 'a booking for the same date' is not mistaken for the Date field."""
    quoted = set(re.findall(_QUOTE, text))
    hits = [f for f in fields if f["label"] in quoted]
    return max(hits, key=lambda f: len(f["label"])) if hits else None


def _validation_rule(when: str, field: Dict[str, Any]) -> Optional[str]:
    """Which rule a validation AC exercises, from its 'when' text."""
    rules = list(field["messages"].keys())
    if _EMPTY_WORDS.search(when) and "required" in rules:
        return "required"
    others = [r for r in rules if r != "required"]
    if len(others) == 1:
        return others[0]
    v = field["validation"]
    number = re.search(r"-?\d+(?:\.\d+)?", when)
    if number:
        n = float(number.group())
        if "min_value" in v and n < v["min_value"]:
            return "min_value"
        if "max_value" in v and n > v["max_value"]:
            return "max_value"
        if "min_length" in v and n < v["min_length"]:
            return "min_length"
        if "max_length" in v and n > v["max_length"]:
            return "max_length"
    return None


def _apply_acceptance_criteria(req: Dict[str, Any], doc: Dict[str, Any], warnings: List[str]) -> List[Dict[str, str]]:
    """Copy texts the acceptance criteria quote literally (rule M1). Returns verbatim_messages."""
    fields = doc["entity"]["fields"]
    by_name = {f["name"]: f for f in fields}
    form_screen = doc["screens"][1]["components"]
    verbatim: List[Dict[str, str]] = []

    def take(path: str, text: str, source: str) -> None:
        if any(vm["path"] == path for vm in verbatim):
            return  # first criterion wins
        verbatim.append({"path": path, "text": text, "source": source})

    save_clicks: Counter = Counter()
    for ac in req.get("acceptance_criteria", []):
        cat, when, then, ac_id = ac["category"], ac["when"], ac["then"], ac["id"]
        clicks = _CLICK_RE.findall(when)
        if cat in ("create", "update", "validation") and clicks:
            save_clicks.update([clicks[-1]])
        if cat == "delete" and clicks:
            take("messages.delete_button", clicks[0], ac_id)
            doc["messages"]["delete_button"] = clicks[0]
            if len(clicks) > 1 and _CONFIRM.search(when):
                take("messages.confirm_button", clicks[1], ac_id)
                doc["messages"]["confirm_button"] = clicks[1]

        quoted = _MESSAGE_RE.findall(then)
        if not quoted:
            continue
        text = quoted[0]
        if cat == "read":
            key = "no_results" if _SEARCH.search(when) else "empty" if _NO_RECORDS.search(then + " " + text) else None
            if key:
                doc["messages"][key] = text
                take(f"messages.{key}", text, ac_id)
        elif cat == "delete" and _CONFIRM.search(then + " " + when):
            doc["messages"]["confirm_delete"] = text
            take("messages.confirm_delete", text, ac_id)
        elif cat == "validation":
            rest = re.sub(r"[\"“«]" + re.escape(text) + r"[\"”»]", " ", then)
            field = _label_in(rest, fields) or _label_in(when, fields)
            rule = _validation_rule(when, field) if field else None
            if field and rule:
                by_name[field["name"]]["messages"][rule] = text
                take(f"entity.fields.{field['name']}.messages.{rule}", text, ac_id)
            else:
                warnings.append(
                    f"{ac_id} quotes the message “{text}” but it is not tied to one field rule (likely a business "
                    "rule such as no double booking); the MVP template cannot show it"
                )

    if save_clicks:
        label, _ = save_clicks.most_common(1)[0]
        button = next(c for c in form_screen if c["type"] == "save_button")
        button["label"] = label
        take("screens.form.save_button", label, next(
            ac["id"] for ac in req.get("acceptance_criteria", []) if label in _CLICK_RE.findall(ac["when"])))
    return verbatim


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
    fields = [_field(f, list_fields, language, t, warnings) for f in e["fields"]]
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

    doc: Dict[str, Any] = {
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
            "empty": t["empty"].format(**fmt), "no_results": t["no_results"], "invalid": t["invalid"],
            "created": t["created"], "updated": t["updated"], "deleted": t["deleted"],
            "confirm_delete": t["confirm_delete"], "confirm_button": t["confirm"],
            "cancel_delete_button": t["cancel_delete"], "edit_button": t["edit"], "delete_button": t["delete"],
        },
        "deferred_rules": deferred,
        "warnings": warnings,
    }
    doc["verbatim_messages"] = _apply_acceptance_criteria(req, doc, warnings)
    # Validation is the contract: if this raises, the mapping above has a bug.
    return ArchitectureDocument.model_validate(doc).model_dump(mode="json", by_alias=True, exclude_none=True)
