"""Deterministic risk rules.

Each rule looks at the facts and, when it applies, adds one risk with its source.
No rule invents information: a risk exists only because something in the other
agents' outputs (or the run itself) points to it.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from .arabic import count as ar
from .facts import RUN_TIME_TARGET_SECONDS, Facts
from .schema import Risk

T = Dict[str, Tuple[str, str]]  # key -> (Arabic, English)

CHECK_NAMES: T = {
    "create_item": ("إضافة سجل", "Create a record"),
    "list_items": ("عرض السجلات", "List records"),
    "edit_item": ("تعديل سجل", "Edit a record"),
    "delete_item": ("حذف سجل", "Delete a record"),
    "persist_after_refresh": ("الحفظ بعد التحديث", "Persist after refresh"),
    "reject_incomplete_input": ("الحقول المطلوبة", "Required fields"),
    "empty_state": ("القائمة الفارغة", "Empty state"),
    "error_message_visible": ("ظهور رسائل الخطأ", "Visible error messages"),
}


def check_name(check_id: str, lang: str) -> str:
    pair = CHECK_NAMES.get(check_id)
    return pair[0 if lang == "ar" else 1] if pair else check_id


def _t(lang: str, ar: str, en: str) -> str:
    return ar if lang == "ar" else en


Draft = Dict[str, str]  # title, likelihood, impact, mitigation, status, source


def _storage(f: Facts) -> List[Draft]:
    engine = f.storage_engine or "localStorage"
    if engine != "localStorage":
        return []
    L = f.language
    return [{
        "title": _t(L, "فقدان البيانات إذا مُسحت بيانات المتصفح", "Data is lost if the browser data is cleared"),
        "likelihood": "medium", "impact": "high",
        "mitigation": _t(L, "رسالة توضيحية داخل التطبيق بأن البيانات محفوظة في المتصفح فقط، والتصدير اليدوي مقترح لنسخة لاحقة.",
                         "A note inside the app that data stays in this browser only; manual export is proposed for a later version."),
        "source": "architecture.entity.storage.engine" if f.has_architecture else "project scope (localStorage)",
    }, {
        "title": _t(L, "الحاجة لاستخدام التطبيق من أكثر من جهاز أو مستخدم", "Need to use the app from more than one device or user"),
        "likelihood": "medium", "impact": "medium",
        "mitigation": _t(L, "خارج نطاق هذه النسخة، ومذكور للمستخدم في المتطلبات.", "Outside this version's scope, and stated in the requirements."),
        "source": "project scope (single user, no server)",
    }]


def _tests(f: Facts) -> List[Draft]:
    L = f.language
    out: List[Draft] = []
    if not f.has_test_report:
        if f.code_done and f.run_completed:
            out.append({
                "title": _t(L, "التطبيق لم يُختبر", "The app was not tested"),
                "likelihood": "high", "impact": "high",
                "mitigation": _t(L, "شغّل فحوصات مختبر الجودة الثمانية قبل التسليم.", "Run the QA Tester's 8 checks before delivery."),
                "source": "test_report.json missing",
            })
        return out
    if f.qa_blocked_reason:
        out.append({
            "title": _t(L, f"تعذّر تشغيل الاختبار: {f.qa_blocked_reason}", f"Tests could not run: {f.qa_blocked_reason}"),
            "likelihood": "high", "impact": "high",
            "mitigation": _t(L, "أصلح سبب التعطل ثم أعد تشغيل الفحوصات.", "Fix the cause, then run the checks again."),
            "source": "test_report.run.blocked_reason",
        })
    for c in f.failed_checks:
        name = check_name(c["id"], L)
        exhausted = f.repair_attempt >= 2
        out.append({
            "title": _t(L, f"فحص «{name}» ما زال يفشل", f"Check “{name}” still fails"),
            "likelihood": "high", "impact": "high",
            "mitigation": _t(L,
                "انتهت محاولتا الإصلاح: سلّم الكود مع تقرير العيوب وراجع الخلل يدوياً." if exhausted else "أُرسل العيب للمطوّر لإصلاحه، ثم تُعاد الفحوصات الثمانية.",
                "Both repair attempts are used: deliver the code with the defect report and fix it by hand." if exhausted else "The defect went back to the Developer; all 8 checks run again after the fix."),
            "source": f"test_report.checks.{c['id']}",
        })
    if f.checks_skipped:
        out.append({
            "title": _t(L, f"لم يعمل {ar(f.checks_skipped, 'check')}", f"{f.checks_skipped} checks did not run"),
            "likelihood": "medium", "impact": "medium",
            "mitigation": _t(L, "راجع سبب التخطي في تقرير الاختبار وأعد التشغيل.", "See why they were skipped in the test report and run again."),
            "source": "test_report.summary.skipped",
        })
    if f.repair_attempt > 0 and f.all_passed:
        out.append({
            "title": _t(L, "فحص فشل في التشغيل الأول", "A check failed on the first run"),
            "likelihood": "low", "impact": "medium",
            "mitigation": _t(L, f"أُغلق: أصلحه المطوّر في المحاولة {f.repair_attempt} من 2، ونجحت الفحوصات كلها بعدها.",
                             f"Closed: the Developer fixed it in attempt {f.repair_attempt} of 2 and all checks passed after."),
            "status": "closed",
            "source": "test_report.run.attempt",
        })
    return out


def _architecture(f: Facts) -> List[Draft]:
    L = f.language
    out: List[Draft] = []
    for i, w in enumerate(f.architecture_warnings):
        out.append({
            "title": _t(L, f"تحذير من المهندس: {w}", f"Architect warning: {w}")[:200],
            "likelihood": "medium", "impact": "medium",
            "mitigation": _t(L, "راجع هذا السلوك يدوياً في المعاينة، أو أضفه في نسخة لاحقة.", "Check this behaviour by hand in the preview, or add it in a later version."),
            "source": f"architecture.warnings[{i}]",
        })
    for i, r in enumerate(f.deferred_rules):
        out.append({
            "title": _t(L, f"قاعدة مؤجلة: {r}", f"Deferred rule: {r}")[:200],
            "likelihood": "medium", "impact": "low",
            "mitigation": _t(L, "القاعدة غير مطبقة في هذه النسخة؛ أبلغ المستخدم بها.", "The rule is not enforced in this version; tell the user."),
            "source": f"architecture.deferred_rules[{i}]",
        })
    return out


def _scope(f: Facts) -> List[Draft]:
    L = f.language
    out: List[Draft] = []
    for o in f.out_of_scope[:3]:
        out.append({
            "title": _t(L, f"طلب ميزة مستبعدة: {o['feature']}", f"Requested feature left out: {o['feature']}")[:200],
            "likelihood": "low", "impact": "medium",
            "mitigation": o["alternative"] or _t(L, "تُناقش في نسخة لاحقة.", "To discuss for a later version."),
            "source": "requirements.out_of_scope",
        })
    if f.assumptions:
        out.append({
            "title": _t(L, f"المتطلبات مبنية على {ar(len(f.assumptions), 'assumption')}", f"Requirements rest on {len(f.assumptions)} assumptions"),
            "likelihood": "medium", "impact": "low",
            "mitigation": _t(L, "راجع الافتراضات مع المستخدم قبل نسخة جديدة.", "Review the assumptions with the user before a new version."),
            "source": "requirements.assumptions",
        })
    return out


def _run(f: Facts) -> List[Draft]:
    L = f.language
    out: List[Draft] = []
    if f.workflow_status in ("failed", "rejected"):
        out.append({
            "title": _t(L, "توقف البناء قبل اكتمال كل المراحل", "The build stopped before all stages finished"),
            "likelihood": "high", "impact": "high",
            "mitigation": _t(L, "المراحل المكتملة محفوظة؛ أعد تشغيل المرحلة المتوقفة.", "Finished stages are kept; run the stopped stage again."),
            "source": f"workflow.status={f.workflow_status}",
        })
    if f.run_time_seconds and f.run_time_seconds > RUN_TIME_TARGET_SECONDS:
        out.append({
            "title": _t(L, f"مدة التشغيل {ar(round(f.run_time_seconds), 'second')}، فوق الهدف ({ar(RUN_TIME_TARGET_SECONDS, 'second')})",
                        f"Run took {round(f.run_time_seconds)} s, above the {RUN_TIME_TARGET_SECONDS} s target"),
            "likelihood": "medium", "impact": "low",
            "mitigation": _t(L, "راجع المرحلة الأطول في الجدول الزمني.", "Look at the longest stage in the timeline."),
            "source": "run_time_seconds",
        })
    return out


RULES: List[Callable[[Facts], List[Draft]]] = [_run, _tests, _storage, _architecture, _scope]
_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_risks(f: Facts) -> List[Risk]:
    drafts: List[Draft] = [d for rule in RULES for d in rule(f)]
    # open before closed, then by impact and likelihood
    drafts.sort(key=lambda d: (d.get("status") == "closed", _ORDER[d["impact"]], _ORDER[d["likelihood"]]))
    return [Risk(id=f"R-{i}", status=d.get("status", "open"), **{k: v for k, v in d.items() if k != "status"})
            for i, d in enumerate(drafts, 1)]
