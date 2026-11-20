"""Read the other agents' outputs into one set of plain facts.

This is the only module that knows the shape of requirements.json, architecture.json
and test_report.json. Everything else (risks, Markdown, the LLM prompt) works from
these facts, so a change in another agent's contract is fixed in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .schema import PMInput

CODE_FILES = ("index.html", "style.css", "app.js")
RUN_TIME_TARGET_SECONDS = 90  # target from the project plan


@dataclass
class Facts:
    language: str
    app_name: str
    app_description: str
    target_users: List[str]
    entities: List[Dict[str, Any]]          # [{name, label, fields: int}]
    field_count: int
    requirement_count: int
    must_count: int
    story_count: int
    criteria_count: int
    assumptions: List[str]
    out_of_scope: List[Dict[str, Any]]      # [{feature, reason, alternative}]
    requirements_status: str
    workflow_status: str

    has_architecture: bool = False
    storage_engine: Optional[str] = None
    screens: List[str] = field(default_factory=list)
    architecture_warnings: List[str] = field(default_factory=list)
    deferred_rules: List[str] = field(default_factory=list)

    generated_files: List[str] = field(default_factory=list)

    has_test_report: bool = False
    checks_total: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    checks_skipped: int = 0
    all_passed: bool = False
    failed_checks: List[Dict[str, str]] = field(default_factory=list)   # [{id, message}]
    qa_attempt: int = 0
    qa_blocked_reason: Optional[str] = None

    repair_attempt: int = 0
    run_time_seconds: Optional[float] = None
    stage_seconds: Dict[str, float] = field(default_factory=dict)

    @property
    def code_done(self) -> bool:
        return all(f in self.generated_files for f in CODE_FILES) or self.has_test_report

    @property
    def run_completed(self) -> bool:
        return self.workflow_status in ("documenting", "completed")


def _text(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ""


def _list(v: Any) -> list:
    return v if isinstance(v, list) else []


def collect(data: PMInput) -> Facts:
    req = data.requirements
    app = req.get("app") or {}
    entities = [
        {"name": _text(e.get("name")), "label": _text(e.get("label")) or _text(e.get("name")),
         "plural": _text(e.get("plural_label")) or _text(e.get("label")) or _text(e.get("name")),
         "fields": len(_list(e.get("fields")))}
        for e in _list(req.get("entities")) if isinstance(e, dict)
    ]
    frs = [r for r in _list(req.get("functional_requirements")) if isinstance(r, dict)]
    oos = [
        {"feature": _text(o.get("feature")), "reason": _text(o.get("reason")), "alternative": _text(o.get("alternative"))}
        for o in _list(req.get("out_of_scope")) if isinstance(o, dict) and _text(o.get("feature"))
    ]
    language = data.language or (req.get("language") if req.get("language") in ("ar", "en") else "ar")

    f = Facts(
        language=language,
        app_name=_text(app.get("name")) or ("التطبيق" if language == "ar" else "The app"),
        app_description=_text(app.get("description")),
        target_users=[u for u in _list(app.get("target_users")) if isinstance(u, str)],
        entities=entities,
        field_count=sum(e["fields"] for e in entities),
        requirement_count=len(frs),
        must_count=sum(1 for r in frs if r.get("priority") == "must"),
        story_count=len(_list(req.get("user_stories"))),
        criteria_count=len(_list(req.get("acceptance_criteria"))),
        assumptions=[a for a in _list(req.get("assumptions")) if isinstance(a, str)],
        out_of_scope=oos,
        requirements_status=_text(req.get("status")) or "ready_for_review",
        workflow_status=data.status,
        generated_files=list(data.generated_files),
        repair_attempt=data.repair_attempt,
        run_time_seconds=data.run_time_seconds,
        stage_seconds=dict(data.stage_seconds),
    )

    arch = data.architecture
    if isinstance(arch, dict) and arch:
        f.has_architecture = True
        entity = arch.get("entity") if isinstance(arch.get("entity"), dict) else {}
        storage = entity.get("storage") if isinstance(entity.get("storage"), dict) else {}
        f.storage_engine = _text(storage.get("engine")) or None
        f.screens = [_text(s.get("title")) or _text(s.get("id")) for s in _list(arch.get("screens")) if isinstance(s, dict)]
        f.architecture_warnings = [w for w in _list(arch.get("warnings")) if isinstance(w, str)]
        f.deferred_rules = [
            _text(r.get("description")) or _text(r.get("rule")) or _text(r.get("id")) if isinstance(r, dict) else str(r)
            for r in _list(arch.get("deferred_rules"))
        ]

    rep = data.test_report
    if isinstance(rep, dict) and rep:
        f.has_test_report = True
        summary = rep.get("summary") if isinstance(rep.get("summary"), dict) else {}
        checks = [c for c in _list(rep.get("checks")) if isinstance(c, dict)]
        f.checks_total = int(summary.get("total") or len(checks))
        f.checks_passed = int(summary.get("passed") or sum(1 for c in checks if c.get("status") == "passed"))
        f.checks_failed = int(summary.get("failed") or sum(1 for c in checks if c.get("status") == "failed"))
        f.checks_skipped = int((summary.get("skipped") or 0) + (summary.get("not_run") or 0))
        f.all_passed = bool(summary.get("all_passed", f.checks_total > 0 and f.checks_passed == f.checks_total))
        f.failed_checks = [
            {"id": _text(c.get("id")), "message": _text((c.get("error") or {}).get("message")) if isinstance(c.get("error"), dict) else ""}
            for c in checks if c.get("status") == "failed"
        ]
        run = rep.get("run") if isinstance(rep.get("run"), dict) else {}
        f.qa_attempt = int(run.get("attempt") or 0)
        f.qa_blocked_reason = _text(run.get("blocked_reason")) or None
        # The QA report is the most reliable source for repairs used.
        f.repair_attempt = max(f.repair_attempt, f.qa_attempt)
    return f
