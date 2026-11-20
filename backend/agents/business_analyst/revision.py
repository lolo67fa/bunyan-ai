"""What really changed between two versions of requirements.json.

After the user asks for changes, the screens show this summary instead of saying
the feedback was applied: an added field is listed only if it is really there, and
an unchanged document is reported as unchanged.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Field properties whose change the user would notice in the generated app.
_FIELD_KEYS = ("label", "type", "required", "enum_values", "default", "validation")
_COUNTED = ("functional_requirements", "user_stories", "acceptance_criteria", "clarification_questions")


def _fields(doc: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    return {
        e.get("name"): {f.get("name"): f for f in e.get("fields") or []}
        for e in doc.get("entities") or []
    }


def summarize_revision(previous: Optional[Dict[str, Any]], current: Dict[str, Any]) -> Dict[str, Any]:
    """Compare the reviewed document with the revised one.

    Returns ``changed`` (anything at all differs, ignoring the copied idea), field
    and entity differences by name, and the before/after count of each list.
    """
    previous = previous or {}
    before, after = _fields(previous), _fields(current)

    added_fields: List[Dict[str, str]] = []
    removed_fields: List[Dict[str, str]] = []
    changed_fields: List[Dict[str, Any]] = []
    for entity in after.keys() & before.keys():
        old, new = before[entity], after[entity]
        added_fields += [{"entity": entity, "field": n, "label": new[n].get("label", n)} for n in new.keys() - old.keys()]
        removed_fields += [{"entity": entity, "field": n, "label": old[n].get("label", n)} for n in old.keys() - new.keys()]
        for n in new.keys() & old.keys():
            what = [k for k in _FIELD_KEYS if old[n].get(k) != new[n].get(k)]
            if what:
                changed_fields.append({"entity": entity, "field": n, "label": new[n].get("label", n), "changed": what})

    counts = {
        key: {"before": len(previous.get(key) or []), "after": len(current.get(key) or [])} for key in _COUNTED
    }
    comparable = lambda d: {k: v for k, v in d.items() if k != "source_idea"}  # noqa: E731
    return {
        "changed": comparable(previous) != comparable(current),
        "status": {"before": previous.get("status"), "after": current.get("status")},
        "added_entities": sorted(after.keys() - before.keys()),
        "removed_entities": sorted(before.keys() - after.keys()),
        "added_fields": sorted(added_fields, key=lambda f: (f["entity"], f["field"])),
        "removed_fields": sorted(removed_fields, key=lambda f: (f["entity"], f["field"])),
        "changed_fields": sorted(changed_fields, key=lambda f: (f["entity"], f["field"])),
        "counts": counts,
    }
