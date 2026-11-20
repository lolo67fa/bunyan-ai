"""Build the stage table and write project_plan.md and risks.md (Arabic or English).

The section order matches the platform's Plan screen: scope, stages, timeline,
status, deliverables. Risks go in their own file.
"""

from __future__ import annotations

from typing import List, Optional

from .arabic import count as ar
from .facts import CODE_FILES, RUN_TIME_TARGET_SECONDS, Facts
from .schema import Risk, Stage

AR = "ar"


def _t(lang: str, ar: str, en: str) -> str:
    return ar if lang == AR else en


LEVEL = {"low": ("منخفض", "Low"), "medium": ("متوسط", "Medium"), "high": ("عالٍ", "High")}
RISK_STATUS = {"open": ("مفتوح", "Open"), "closed": ("مغلق", "Closed")}
STAGE_STATUS = {
    "done": ("مكتمل", "Done"), "in_progress": ("جارٍ", "In progress"),
    "failed": ("متوقف", "Stopped"), "not_started": ("لم يبدأ", "Not started"),
}
STAGE_NAME = {
    "requirements": ("اعتماد المتطلبات", "Requirements approval"),
    "structure": ("تصميم الهيكل", "Structure design"),
    "development": ("كتابة الكود", "Code"),
    "tests": ("اختبار الجودة", "Quality tests"),
    "documentation": ("التسليم والتوثيق", "Delivery and documents"),
}


def _w(pair, lang: str) -> str:
    return pair[0 if lang == AR else 1]


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _duration(seconds: Optional[float], lang: str) -> str:
    if seconds is None:
        return "—"
    s = int(round(seconds))
    if s < 60:
        return _t(lang, ar(s, "second"), f"{s} s")
    return _t(lang, f"{s // 60}:{s % 60:02d} دقيقة", f"{s // 60} min {s % 60:02d} s")


def build_stages(f: Facts) -> List[Stage]:
    L = f.language
    req_done = f.requirements_status == "ready_for_review" and f.workflow_status not in (
        "created", "analyzing", "awaiting_clarification", "awaiting_approval", "rejected")
    tests_status = "not_started"
    if f.has_test_report:
        if f.all_passed:
            tests_status = "done"
        elif f.repair_attempt >= 2 or f.qa_blocked_reason:
            tests_status = "failed"
        else:
            tests_status = "in_progress"
    done = {
        "requirements": "done" if req_done else "not_started",
        "structure": "done" if f.has_architecture else "not_started",
        "development": "done" if f.code_done else "not_started",
        "tests": tests_status,
        "documentation": "done",
    }
    # The first unfinished stage is either running or where the run stopped.
    order = ["requirements", "structure", "development", "tests"]
    for key in order:
        if done[key] == "not_started":
            done[key] = "failed" if f.workflow_status in ("failed", "rejected") else "in_progress"
            break

    entity_word = _t(L, ar(len(f.entities), "entity"), "1 entity" if len(f.entities) == 1 else f"{len(f.entities)} entities")
    screens = len(f.screens) or 2
    outputs = {
        "requirements": _t(L, f"{ar(f.field_count, 'field')}، {ar(f.requirement_count, 'requirement')}، {ar(f.story_count, 'story')}",
                           f"{f.field_count} fields, {f.requirement_count} requirements, {f.story_count} user stories"),
        "structure": _t(L, f"نموذج البيانات والشاشات والتحقق ({entity_word}، {ar(screens, 'screen')})",
                        f"Data model, screens and validation ({entity_word}, {screens} screens)"),
        "development": " · ".join(f.generated_files or CODE_FILES),
        "tests": (_t(L, f"نجح {f.checks_passed} من {ar(f.checks_total, 'check')}", f"{f.checks_passed} of {f.checks_total} checks passed")
                  + (_t(L, f" بعد {ar(f.repair_attempt, 'repair')}", f" after {f.repair_attempt} repair{'s' if f.repair_attempt > 1 else ''}") if f.repair_attempt else ""))
                 if f.has_test_report else _t(L, "8 فحوصات في متصفح حقيقي", "8 checks in a real browser"),
        "documentation": "project_plan.md · risks.md",
    }
    owners = {
        "requirements": _t(L, "محلّل الأعمال والمستخدم", "Business Analyst and the user"),
        "structure": _t(L, "المهندس", "Architect"),
        "development": _t(L, "المطوّر", "Developer"),
        "tests": _t(L, "مختبر الجودة", "QA Tester"),
        "documentation": _t(L, "مدير المشروع", "Project Manager"),
    }
    return [Stage(key=k, owner=owners[k], output=outputs[k], status=done[k], seconds=f.stage_seconds.get(k))
            for k in ["requirements", "structure", "development", "tests", "documentation"]]


def rules_summary(f: Facts, stages: List[Stage], risks: List[Risk]) -> str:
    L = f.language
    open_risks = sum(1 for r in risks if r.status == "open")
    finished = all(s.status == "done" for s in stages)
    if finished and f.all_passed:
        head = _t(L, f"اكتمل {f.app_name} واجتاز {f.checks_passed} من {ar(f.checks_total, 'check')}",
                  f"{f.app_name} is complete and passed {f.checks_passed} of {f.checks_total} checks")
        if f.repair_attempt:
            head += _t(L, f" بعد {ar(f.repair_attempt, 'repair')}", f" after {f.repair_attempt} repair{'s' if f.repair_attempt > 1 else ''}")
    elif f.has_test_report and not f.all_passed:
        head = _t(L, f"اكتمل الكود لكن {f.checks_failed} من {ar(f.checks_total, 'check')} ما زالت تفشل",
                  f"The code is done but {f.checks_failed} of {f.checks_total} checks still {'fails' if f.checks_failed == 1 else 'fail'}")
    else:
        current = next((s for s in stages if s.status != "done"), None)
        name = _w(STAGE_NAME[current.key], L) if current else ""
        head = _t(L, f"البناء لم يكتمل؛ توقف عند: {name}", f"The build is not complete; it stopped at: {name}")
    tail = _t(L, f". المخاطر المفتوحة: {open_risks}.", f". Open risks: {open_risks}.")
    return head + tail


def plan_markdown(f: Facts, stages: List[Stage], risks: List[Risk], summary: str) -> str:
    L = f.language
    lines: List[str] = [f"# {_t(L, 'خطة المشروع', 'Project plan')}: {f.app_name}", "", f"> {summary}", ""]

    # Scope
    lines += [f"## {_t(L, 'النطاق', 'Scope')}", ""]
    if f.app_description:
        lines += [f.app_description, ""]
    entities = _t(L, "، ", ", ").join(e["plural"] for e in f.entities) or "—"
    lines.append(_t(L,
        f"- **يشمل:** {entities}: الإضافة والعرض والتعديل والحذف، مع البحث والترتيب والتحقق من الحقول.",
        f"- **Includes:** {entities}: create, read, update and delete, with search, sorting and field validation."))
    excluded = [o["feature"] for o in f.out_of_scope] or [
        _t(L, "تعدد المستخدمين", "multiple users"), _t(L, "المزامنة السحابية", "cloud sync"), _t(L, "التقارير", "reports")]
    lines.append(_t(L, f"- **لا يشمل:** {'، '.join(excluded)}.", f"- **Excludes:** {', '.join(excluded)}."))
    if f.target_users:
        lines.append(_t(L, f"- **المستخدمون:** {'، '.join(f.target_users)}.", f"- **Users:** {', '.join(f.target_users)}."))
    lines.append("")

    # Stages
    head = _t(L, "| المرحلة | المسؤول | المخرج | الحالة |", "| Stage | Owner | Output | Status |")
    lines += [f"## {_t(L, 'المراحل', 'Stages')}", "", head, "|---|---|---|---|"]
    for s in stages:
        lines.append(f"| {_w(STAGE_NAME[s.key], L)} | {_cell(s.owner)} | {_cell(s.output)} | {_w(STAGE_STATUS[s.status], L)} |")
    lines.append("")

    # Timeline
    lines += [f"## {_t(L, 'الجدول الزمني', 'Timeline')}", ""]
    if any(s.seconds is not None for s in stages) or f.run_time_seconds:
        lines += [_t(L, "| المرحلة | المدة |", "| Stage | Duration |"), "|---|---|"]
        for s in stages:
            if s.seconds is not None:
                lines.append(f"| {_w(STAGE_NAME[s.key], L)} | {_duration(s.seconds, L)} |")
        if f.run_time_seconds:
            within = f.run_time_seconds <= RUN_TIME_TARGET_SECONDS
            lines.append(_t(L,
                f"| **المجموع** | **{_duration(f.run_time_seconds, L)}** ({'ضمن' if within else 'فوق'} الهدف: {ar(RUN_TIME_TARGET_SECONDS, 'second')}) |",
                f"| **Total** | **{_duration(f.run_time_seconds, L)}** ({'within' if within else 'above'} the {RUN_TIME_TARGET_SECONDS} s target) |"))
    else:
        lines.append(_t(L, "لم تُسجَّل مدد المراحل في هذا التشغيل. الترتيب: المتطلبات، الهيكل، الكود، الاختبار، التسليم.",
                        "Stage durations were not recorded in this run. Order: requirements, structure, code, tests, delivery."))
    lines.append("")

    # Status
    open_risks = [r for r in risks if r.status == "open"]
    lines += [f"## {_t(L, 'حالة المشروع', 'Status')}", ""]
    if f.has_test_report:
        lines.append(_t(L, f"- **الاختبار:** نجح {f.checks_passed} من {ar(f.checks_total, 'check')}.", f"- **Tests:** {f.checks_passed} of {f.checks_total} passed."))
    lines.append(_t(L, f"- **محاولات الإصلاح:** {f.repair_attempt} من 2.", f"- **Repair attempts:** {f.repair_attempt} of 2."))
    lines.append(_t(L, f"- **المتطلبات:** {ar(f.requirement_count, 'requirement')} (منها {f.must_count} إلزامية)، و{ar(f.criteria_count, 'criterion')}.",
                    f"- **Requirements:** {f.requirement_count} ({f.must_count} must), {f.criteria_count} acceptance criteria."))
    lines.append(_t(L, f"- **المخاطر المفتوحة:** {len(open_risks)}، تفاصيلها في `risks.md`.",
                    f"- **Open risks:** {len(open_risks)}, see `risks.md`."))
    lines.append("")

    # Deliverables
    lines += [f"## {_t(L, 'المخرجات', 'Deliverables')}", ""]
    files = [("requirements.json", _t(L, "المتطلبات المعتمدة", "Approved requirements"))]
    if f.has_architecture:
        files.append(("architecture.json", _t(L, "وثيقة الهيكل", "Structure document")))
    for name in f.generated_files or (CODE_FILES if f.code_done else []):
        files.append((name, _t(L, "كود التطبيق", "App code")))
    if f.has_test_report:
        files.append(("test_report.json", _t(L, "تقرير الاختبار", "Test report")))
    files += [("project_plan.md", _t(L, "هذه الخطة", "This plan")), ("risks.md", _t(L, "المخاطر", "Risks"))]
    lines += [f"- `{n}`: {d}" for n, d in files]
    lines.append("")
    return "\n".join(lines)


def risks_markdown(f: Facts, risks: List[Risk]) -> str:
    L = f.language
    lines = [f"# {_t(L, 'المخاطر', 'Risks')}: {f.app_name}", ""]
    if not risks:
        lines += [_t(L, "لا توجد مخاطر مسجلة.", "No risks recorded."), ""]
        return "\n".join(lines)
    lines += [_t(L, "| # | الخطر | الاحتمال | الأثر | المعالجة | الحالة |", "| # | Risk | Likelihood | Impact | Mitigation | Status |"),
              "|---|---|---|---|---|---|"]
    for r in risks:
        lines.append(f"| {r.id} | {_cell(r.title)} | {_w(LEVEL[r.likelihood], L)} | {_w(LEVEL[r.impact], L)} | "
                     f"{_cell(r.mitigation)} | {_w(RISK_STATUS[r.status], L)} |")
    lines += ["", f"### {_t(L, 'مصدر كل خطر', 'Where each risk comes from')}", ""]
    lines += [f"- {r.id}: `{r.source}`" for r in risks]
    lines.append("")
    return "\n".join(lines)
