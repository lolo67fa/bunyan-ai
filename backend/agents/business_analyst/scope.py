"""Deterministic CRUD MVP scope guard.

Runs on the user's idea (to flag requests before analysis) and on the final
requirements document (to catch an LLM that slipped an out-of-scope feature
into the in-scope requirements). It does not call any model.

English patterns are regular expressions matched on word boundaries. Arabic
patterns are plain substrings because Arabic attaches prefixes such as
"ال" / "و" / "ب" directly to words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .schema import OutOfScopeItem, RequirementsDocument


@dataclass(frozen=True)
class ScopeRule:
    category: str
    en_patterns: Tuple[str, ...]
    ar_patterns: Tuple[str, ...]
    feature: Dict[str, str]
    reason: Dict[str, str]
    alternative: Optional[Dict[str, str]] = None


RULES: Tuple[ScopeRule, ...] = (
    ScopeRule(
        category="authentication",
        en_patterns=(r"log ?in", r"sign ?in", r"sign ?up", r"password", r"user accounts?", r"authenticat\w*",
                     r"roles? and permissions", r"admin (panel|accounts?)", r"oauth", r"two[- ]factor"),
        ar_patterns=("تسجيل الدخول", "تسجيل دخول", "كلمة المرور", "كلمة مرور", "حسابات المستخدمين",
                     "إنشاء حساب", "انشاء حساب", "صلاحيات"),
        feature={"en": "User accounts / login", "ar": "حسابات المستخدمين وتسجيل الدخول"},
        reason={"en": "Generated apps are single-user and run in the browser without authentication.",
                "ar": "التطبيقات المولدة لمستخدم واحد وتعمل في المتصفح دون نظام تسجيل دخول."},
    ),
    ScopeRule(
        category="payments",
        en_patterns=(r"pay online", r"online payments?", r"payment gateway", r"accept payments?",
                     r"process(ing)? payments?", r"credit cards?", r"online checkout", r"checkout page", r"stripe", r"paypal",
                     r"apple pay"),
        ar_patterns=("الدفع الإلكتروني", "الدفع الالكتروني", "دفع إلكتروني", "بوابة دفع", "بوابة الدفع",
                     "بطاقة ائتمان", "بطاقات ائتمان", "الدفع أونلاين", "الدفع اونلاين", "أبل باي"),
        feature={"en": "Online payment processing", "ar": "معالجة المدفوعات الإلكترونية"},
        reason={"en": "Payment processing is excluded from the CRUD MVP.",
                "ar": "معالجة المدفوعات خارج نطاق النسخة الأولى (CRUD)."},
        alternative={"en": "Record payment status (e.g. paid / unpaid) as a normal field.",
                     "ar": "تسجيل حالة الدفع (مدفوع / غير مدفوع) كحقل عادي."},
    ),
    ScopeRule(
        category="native_mobile",
        en_patterns=(r"ios app", r"android app", r"iphone app", r"native (mobile )?app", r"mobile app",
                     r"app store", r"google play", r"push notifications?"),
        ar_patterns=("تطبيق جوال", "تطبيق الجوال", "تطبيق للجوال", "تطبيق آيفون", "تطبيق ايفون",
                     "تطبيق أندرويد", "تطبيق اندرويد", "متجر التطبيقات", "إشعارات فورية"),
        feature={"en": "Native mobile app", "ar": "تطبيق جوال أصلي"},
        reason={"en": "Only browser-based web apps are generated.",
                "ar": "يتم توليد تطبيقات ويب تعمل في المتصفح فقط."},
        alternative={"en": "A responsive web app that also works in a mobile browser.",
                     "ar": "تطبيق ويب متجاوب يعمل أيضاً في متصفح الجوال."},
    ),
    ScopeRule(
        category="realtime_collaboration",
        en_patterns=(r"real[- ]time (collaboration|chat|sync\w*)", r"live chat", r"chat with", r"multi[- ]?user", r"share [\w ]{0,20}?with (my |the |other )?(team|users|colleagues|friends|family)",
                     r"collaborat\w*", r"sync(ed|hroni[sz]ed)? across devices"),
        ar_patterns=("تعاون في الوقت الفعلي", "محادثة مباشرة", "دردشة", "عدة مستخدمين", "مشاركة مع الفريق",
                     "مزامنة بين الأجهزة"),
        feature={"en": "Multi-user / real-time collaboration", "ar": "التعاون بين عدة مستخدمين في الوقت الفعلي"},
        reason={"en": "Data is stored in localStorage, so it is local to one browser.",
                "ar": "تُحفظ البيانات في localStorage فهي خاصة بمتصفح واحد."},
    ),
    ScopeRule(
        category="external_integration",
        en_patterns=(r"send (an )?emails?", r"email notifications?", r"sms", r"whatsapp", r"google calendar",
                     r"\bapi integration", r"integrat\w* with", r"third[- ]party api"),
        ar_patterns=("إرسال بريد", "ارسال بريد", "رسائل نصية", "رسالة نصية", "واتساب", "تقويم جوجل", "ربط مع"),
        feature={"en": "Messaging or third-party integration", "ar": "الرسائل أو الربط مع خدمات خارجية"},
        reason={"en": "Generated apps have no server and cannot send messages or call external services.",
                "ar": "التطبيقات المولدة بلا خادم ولا يمكنها إرسال رسائل أو الاتصال بخدمات خارجية."},
        alternative={"en": "Show reminders inside the app (e.g. highlight records due today).",
                     "ar": "عرض التذكيرات داخل التطبيق (مثل تمييز السجلات المستحقة اليوم)."},
    ),
    ScopeRule(
        category="server_backend",
        en_patterns=(r"backend server", r"rest api", r"server[- ]side", r"(sql|mysql|postgres\w*|mongo\w*) database",
                     r"cloud database", r"firebase"),
        ar_patterns=("خادم خلفي", "قاعدة بيانات سحابية", "قاعدة بيانات على الخادم"),
        feature={"en": "Custom backend / server database", "ar": "خادم خلفي أو قاعدة بيانات على الخادم"},
        reason={"en": "Generated apps persist data in browser localStorage only.",
                "ar": "التطبيقات المولدة تحفظ البيانات في localStorage في المتصفح فقط."},
        alternative={"en": "Persist records in browser localStorage.", "ar": "حفظ السجلات في localStorage."},
    ),
    ScopeRule(
        category="enterprise_system",
        en_patterns=(r"\berp\b", r"\bcrm\b", r"payroll", r"accounting system", r"enterprise (system|resource planning)"),
        ar_patterns=("نظام تخطيط موارد", "نظام محاسبي", "مسير الرواتب", "نظام رواتب", "إدارة علاقات العملاء"),
        feature={"en": "Enterprise system (ERP / CRM / payroll)", "ar": "نظام مؤسسي (ERP / CRM / رواتب)"},
        reason={"en": "Enterprise systems are excluded from the CRUD MVP.",
                "ar": "الأنظمة المؤسسية خارج نطاق النسخة الأولى."},
    ),
    ScopeRule(
        category="file_storage",
        en_patterns=(r"upload (photos?|images?|files?|documents?|attachments?)", r"file uploads?", r"attachments?"),
        ar_patterns=("رفع الصور", "رفع صور", "رفع ملفات", "رفع الملفات", "مرفقات"),
        feature={"en": "File / image uploads", "ar": "رفع الملفات والصور"},
        reason={"en": "localStorage cannot reliably store files.",
                "ar": "لا يمكن تخزين الملفات بشكل موثوق في localStorage."},
        alternative={"en": "Store a link (URL) to the file instead.", "ar": "حفظ رابط (URL) للملف بدلاً من ذلك."},
    ),
)

_COMPILED = [
    (rule, [re.compile(rf"\b{p}\b", re.IGNORECASE) for p in rule.en_patterns])
    for rule in RULES
]


def _matching_rules(text: str) -> List[Tuple[ScopeRule, str]]:
    hits: List[Tuple[ScopeRule, str]] = []
    for rule, regexes in _COMPILED:
        match = next((m.group(0) for r in regexes if (m := r.search(text))), None)
        if match is None:
            match = next((p for p in rule.ar_patterns if p in text), None)
        if match is not None:
            hits.append((rule, match))
    return hits


def detect_out_of_scope(text: str, language: str = "en") -> List[OutOfScopeItem]:
    """Flag out-of-scope features mentioned in free text (idea or answers)."""
    items = []
    for rule, matched in _matching_rules(text):
        has_alt = rule.alternative is not None
        items.append(
            OutOfScopeItem(
                feature=f"{rule.feature[language]} ('{matched}')",
                category=rule.category,
                reason=rule.reason[language],
                action="replaced_with_crud_alternative" if has_alt else "excluded",
                alternative=rule.alternative[language] if has_alt else None,
            )
        )
    return items


def merge_out_of_scope(existing: Iterable[OutOfScopeItem], extra: Iterable[OutOfScopeItem]) -> List[OutOfScopeItem]:
    """Add guard-detected items whose category the analyst did not already flag."""
    result = list(existing)
    seen = {i.category for i in result}
    for item in extra:
        if item.category not in seen:
            result.append(item)
            seen.add(item.category)
    return result


@dataclass(frozen=True)
class ScopeViolation:
    location: str
    category: str
    matched: str

    def __str__(self) -> str:
        return f"{self.location}: out-of-scope '{self.category}' feature ('{self.matched}')"


def find_scope_violations(doc: RequirementsDocument) -> List[ScopeViolation]:
    """Find out-of-scope features inside the *in-scope* parts of a document.

    Only requirements, user stories and acceptance criteria are scanned; the
    ``out_of_scope`` list and clarification questions are allowed to mention
    such features. CRUD alternatives (e.g. a ``payment_status`` field) do not
    match because the patterns target processing, not data.
    """
    texts: List[Tuple[str, str]] = []
    for r in doc.functional_requirements:
        texts.append((r.id, r.description))
    for s in doc.user_stories:
        texts.append((s.id, f"{s.goal} {s.benefit}"))
    for a in doc.acceptance_criteria:
        texts.append((a.id, f"{a.given} {a.when} {a.then}"))
    violations = []
    for location, text in texts:
        for rule, matched in _matching_rules(text):
            violations.append(ScopeViolation(location, rule.category, matched))
    for e in doc.entities:
        for f in e.fields:
            if f.name in {"password", "password_hash"}:
                violations.append(ScopeViolation(f"{e.name}.{f.name}", "authentication", f.name))
            if f.name in {"card_number", "cvv"}:
                violations.append(ScopeViolation(f"{e.name}.{f.name}", "payments", f.name))
    return _dedupe(violations)


def _dedupe(violations: List[ScopeViolation]) -> List[ScopeViolation]:
    seen = set()
    out = []
    for v in violations:
        key = (v.location, v.category)
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out
