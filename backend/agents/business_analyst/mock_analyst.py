"""Mock mode: a deterministic, offline stand-in for the LLM.

It is NOT a real analysis. It recognises three demo domains (task manager,
inventory manager, appointment booking) by keyword, fills a hand-written
template in English or Arabic, and returns the same kind of raw JSON string an
LLM would. The result then goes through exactly the same parsing, scope guard
and Pydantic validation as a real LLM answer, which lets you test the contract
and the pipeline without API calls or cost.

Ideas that match no domain produce ``needs_clarification`` (or
``rejected_out_of_scope`` when they only ask for out-of-scope features).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .scope import detect_out_of_scope

L = Dict[str, str]  # {"en": ..., "ar": ...}


@dataclass
class FieldSpec:
    name: str
    label: L
    type: str
    required: bool
    sample: L                       # value used in acceptance criteria
    unique: bool = False
    enum_values: Optional[Dict[str, List[str]]] = None
    reference_entity: Optional[str] = None
    default_index: Optional[int] = None  # index into enum_values
    default: Any = None
    validation: Dict[str, Any] = field(default_factory=dict)
    invalid: Optional[L] = None     # description of an input that breaks `validation`


@dataclass
class EntitySpec:
    name: str
    label: L
    plural: L
    description: L
    display_field: str
    fields: List[FieldSpec]
    list_fields: List[str]
    search_fields: List[str]
    filter_fields: List[str]
    sort_field: str
    sort_direction: str = "asc"


@dataclass
class ExtraRule:
    entity: str
    requirement: L
    given: L
    when: L
    then: L


@dataclass
class DomainSpec:
    key: str
    keywords_en: Tuple[str, ...]
    keywords_ar: Tuple[str, ...]
    app_name: L
    description: L
    role: L
    target_users: Dict[str, List[str]]
    entities: List[EntitySpec]
    extra_rules: List[ExtraRule] = field(default_factory=list)
    assumptions: Dict[str, List[str]] = field(default_factory=dict)
    optional_questions: List[Dict[str, Any]] = field(default_factory=list)


# --------------------------------------------------------------------------------------
# Domain templates
# --------------------------------------------------------------------------------------

TASK_MANAGER = DomainSpec(
    key="task_manager",
    keywords_en=("task", "tasks", "to-do", "todo", "to do"),
    keywords_ar=("مهام", "مهمة", "المهام", "مهمات"),
    app_name={"en": "Task Manager", "ar": "مدير المهام"},
    description={
        "en": "A single-user web app to create, track, update and delete personal tasks with due dates, priority and status.",
        "ar": "تطبيق ويب لمستخدم واحد لإنشاء المهام الشخصية ومتابعتها وتعديلها وحذفها مع تاريخ الاستحقاق والأولوية والحالة.",
    },
    role={"en": "user", "ar": "مستخدم"},
    target_users={"en": ["Students", "Individual professionals"], "ar": ["الطلاب", "الموظفون الأفراد"]},
    entities=[
        EntitySpec(
            name="Task",
            label={"en": "Task", "ar": "مهمة"},
            plural={"en": "Tasks", "ar": "المهام"},
            description={"en": "A piece of work the user needs to do.", "ar": "عمل يحتاج المستخدم إلى إنجازه."},
            display_field="title",
            fields=[
                FieldSpec("title", {"en": "Title", "ar": "العنوان"}, "string", True,
                          sample={"en": "Prepare sprint report", "ar": "إعداد تقرير الأسبوع"},
                          validation={"min_length": 3, "max_length": 100},
                          invalid={"en": "the 2-character value \"ab\"", "ar": "القيمة \"اب\" المكونة من حرفين"}),
                FieldSpec("description", {"en": "Description", "ar": "الوصف"}, "text", False,
                          sample={"en": "Include charts for completed tasks", "ar": "إضافة رسوم للمهام المكتملة"},
                          validation={"max_length": 1000},
                          invalid={"en": "a text of 1001 characters", "ar": "نصاً من 1001 حرف"}),
                FieldSpec("due_date", {"en": "Due date", "ar": "تاريخ الاستحقاق"}, "date", False,
                          sample={"en": "a date 7 days from today", "ar": "تاريخ بعد 7 أيام من اليوم"},
                          validation={"date_constraint": "not_in_past"},
                          invalid={"en": "yesterday's date", "ar": "تاريخ الأمس"}),
                FieldSpec("priority", {"en": "Priority", "ar": "الأولوية"}, "enum", True,
                          sample={"en": "high", "ar": "عالية"},
                          enum_values={"en": ["low", "medium", "high"], "ar": ["منخفضة", "متوسطة", "عالية"]},
                          default_index=1),
                FieldSpec("status", {"en": "Status", "ar": "الحالة"}, "enum", True,
                          sample={"en": "to_do", "ar": "جديدة"},
                          enum_values={"en": ["to_do", "in_progress", "done"], "ar": ["جديدة", "قيد التنفيذ", "مكتملة"]},
                          default_index=0),
            ],
            list_fields=["title", "due_date", "priority", "status"],
            search_fields=["title"],
            filter_fields=["status", "priority"],
            sort_field="due_date",
        )
    ],
    assumptions={
        "en": ["Tasks have no sub-tasks or assignees in the MVP."],
        "ar": ["لا تحتوي المهام على مهام فرعية أو مسؤولين في النسخة الأولى."],
    },
    optional_questions=[
        {"en": "Do you want to group tasks into categories or projects?",
         "ar": "هل تريد تصنيف المهام ضمن فئات أو مشاريع؟",
         "reason_en": "Categories would add a second entity.",
         "reason_ar": "إضافة الفئات تعني كياناً ثانياً.",
         "default_en": "No categories in the first version.", "default_ar": "بدون فئات في النسخة الأولى."},
    ],
)

INVENTORY_MANAGER = DomainSpec(
    key="inventory_manager",
    keywords_en=("inventory", "stock", "warehouse", "products", "items"),
    keywords_ar=("مخزون", "المخزون", "مستودع", "المستودع", "منتجات", "المنتجات", "بضاعة", "البضائع"),
    app_name={"en": "Inventory Manager", "ar": "مدير المخزون"},
    description={
        "en": "A web app for a small shop to manage product categories and stock items, including quantities, prices and reorder levels.",
        "ar": "تطبيق ويب لمتجر صغير لإدارة فئات المنتجات وأصناف المخزون مع الكميات والأسعار وحد إعادة الطلب.",
    },
    role={"en": "shop owner", "ar": "صاحب المتجر"},
    target_users={"en": ["Small shop owners", "Store keepers"], "ar": ["أصحاب المتاجر الصغيرة", "أمناء المستودعات"]},
    entities=[
        EntitySpec(
            name="Category",
            label={"en": "Category", "ar": "فئة"},
            plural={"en": "Categories", "ar": "الفئات"},
            description={"en": "A group of related products.", "ar": "مجموعة من المنتجات المتشابهة."},
            display_field="name",
            fields=[
                FieldSpec("name", {"en": "Name", "ar": "الاسم"}, "string", True, unique=True,
                          sample={"en": "Beverages", "ar": "مشروبات"},
                          validation={"min_length": 2, "max_length": 50},
                          invalid={"en": "the 1-character value \"B\"", "ar": "القيمة \"م\" المكونة من حرف واحد"}),
                FieldSpec("description", {"en": "Description", "ar": "الوصف"}, "text", False,
                          sample={"en": "Cold and hot drinks", "ar": "مشروبات باردة وساخنة"},
                          validation={"max_length": 300},
                          invalid={"en": "a text of 301 characters", "ar": "نصاً من 301 حرف"}),
            ],
            list_fields=["name", "description"],
            search_fields=["name"],
            filter_fields=[],
            sort_field="name",
        ),
        EntitySpec(
            name="Item",
            label={"en": "Item", "ar": "صنف"},
            plural={"en": "Items", "ar": "الأصناف"},
            description={"en": "A product kept in stock.", "ar": "منتج موجود في المخزون."},
            display_field="name",
            fields=[
                FieldSpec("name", {"en": "Name", "ar": "اسم الصنف"}, "string", True,
                          sample={"en": "Mineral water 330ml", "ar": "مياه معدنية 330 مل"},
                          validation={"min_length": 2, "max_length": 100},
                          invalid={"en": "the 1-character value \"W\"", "ar": "القيمة \"م\" المكونة من حرف واحد"}),
                FieldSpec("sku", {"en": "SKU", "ar": "رمز الصنف (SKU)"}, "string", True, unique=True,
                          sample={"en": "WTR-330", "ar": "WTR-330"},
                          validation={"pattern": "^[A-Z0-9-]{3,20}$"},
                          invalid={"en": "the value \"wtr 330\" (lowercase letters and a space)",
                                   "ar": "القيمة \"wtr 330\" (حروف صغيرة ومسافة)"}),
                FieldSpec("category", {"en": "Category", "ar": "الفئة"}, "reference", False,
                          reference_entity="Category",
                          sample={"en": "Beverages", "ar": "مشروبات"}),
                FieldSpec("quantity", {"en": "Quantity", "ar": "الكمية"}, "integer", True, default=0,
                          sample={"en": "24", "ar": "24"},
                          validation={"min_value": 0},
                          invalid={"en": "the value -1", "ar": "القيمة -1"}),
                FieldSpec("unit_price", {"en": "Unit price (SAR)", "ar": "سعر الوحدة (ريال)"}, "decimal", True,
                          sample={"en": "2.50", "ar": "2.50"},
                          validation={"min_value": 0},
                          invalid={"en": "the value -5", "ar": "القيمة -5"}),
                FieldSpec("reorder_level", {"en": "Reorder level", "ar": "حد إعادة الطلب"}, "integer", False,
                          sample={"en": "10", "ar": "10"},
                          validation={"min_value": 0},
                          invalid={"en": "the value -1", "ar": "القيمة -1"}),
            ],
            list_fields=["name", "sku", "category", "quantity", "unit_price"],
            search_fields=["name", "sku"],
            filter_fields=["category"],
            sort_field="name",
        ),
    ],
    extra_rules=[
        ExtraRule(
            entity="Item",
            requirement={
                "en": "The system shall mark an Item as 'Low stock' in the list when its quantity is less than or equal to its reorder level.",
                "ar": "يجب أن يميز النظام الصنف بعلامة \"مخزون منخفض\" في القائمة عندما تكون كميته أقل من أو تساوي حد إعادة الطلب.",
            },
            given={"en": "an Item with quantity 5 and reorder level 10 exists",
                   "ar": "يوجد صنف كميته 5 وحد إعادة الطلب له 10"},
            when={"en": "the user opens the Items list", "ar": "يفتح المستخدم قائمة الأصناف"},
            then={"en": "that Item's row shows the label \"Low stock\"",
                  "ar": "يظهر في صف هذا الصنف الوسم \"مخزون منخفض\""},
        ),
    ],
    assumptions={
        "en": ["Stock movements (purchases/sales history) are not tracked; the user edits the quantity directly.",
               "Prices are in Saudi Riyal (SAR)."],
        "ar": ["لا يتم تتبع حركات المخزون (سجل المشتريات والمبيعات)؛ يعدّل المستخدم الكمية مباشرة.",
               "الأسعار بالريال السعودي."],
    },
    optional_questions=[
        {"en": "Should deleting a Category also delete its Items, or should it be blocked while Items use it?",
         "ar": "عند حذف فئة، هل تُحذف أصنافها أيضاً أم يُمنع الحذف ما دامت مستخدمة؟",
         "reason_en": "Defines delete behaviour for related records.",
         "reason_ar": "يحدد سلوك الحذف للسجلات المرتبطة.",
         "default_en": "Block deleting a Category that still has Items.",
         "default_ar": "منع حذف الفئة إذا كانت تحتوي على أصناف."},
    ],
)

APPOINTMENT_BOOKING = DomainSpec(
    key="appointment_booking",
    keywords_en=("appointment", "appointments", "booking", "bookings", "reservation", "clinic", "salon", "schedule"),
    keywords_ar=("موعد", "مواعيد", "المواعيد", "حجز", "حجوزات", "عيادة", "صالون"),
    app_name={"en": "Appointment Booking", "ar": "حجز المواعيد"},
    description={
        "en": "A web app for a small clinic receptionist to book, view, reschedule and cancel client appointments.",
        "ar": "تطبيق ويب لموظف استقبال في عيادة صغيرة لحجز مواعيد العملاء وعرضها وتعديلها وإلغائها.",
    },
    role={"en": "receptionist", "ar": "موظف الاستقبال"},
    target_users={"en": ["Clinic receptionists", "Small service businesses"], "ar": ["موظفو الاستقبال في العيادات", "الأعمال الخدمية الصغيرة"]},
    entities=[
        EntitySpec(
            name="Appointment",
            label={"en": "Appointment", "ar": "موعد"},
            plural={"en": "Appointments", "ar": "المواعيد"},
            description={"en": "A booked time slot for a client.", "ar": "وقت محجوز لعميل."},
            display_field="client_name",
            fields=[
                FieldSpec("client_name", {"en": "Client name", "ar": "اسم العميل"}, "string", True,
                          sample={"en": "Sara Ahmed", "ar": "سارة أحمد"},
                          validation={"min_length": 2, "max_length": 100},
                          invalid={"en": "the 1-character value \"S\"", "ar": "القيمة \"س\" المكونة من حرف واحد"}),
                FieldSpec("client_phone", {"en": "Client phone", "ar": "جوال العميل"}, "phone", True,
                          sample={"en": "0551234567", "ar": "0551234567"},
                          validation={"pattern": "^\\+?[0-9]{9,15}$"},
                          invalid={"en": "the value \"abc123\"", "ar": "القيمة \"abc123\""}),
                FieldSpec("service", {"en": "Service", "ar": "الخدمة"}, "enum", True,
                          sample={"en": "consultation", "ar": "استشارة"},
                          enum_values={"en": ["consultation", "follow_up", "check_up"],
                                       "ar": ["استشارة", "مراجعة", "فحص"]}),
                FieldSpec("date", {"en": "Date", "ar": "التاريخ"}, "date", True,
                          sample={"en": "a date 3 days from today", "ar": "تاريخ بعد 3 أيام من اليوم"},
                          validation={"date_constraint": "not_in_past"},
                          invalid={"en": "yesterday's date", "ar": "تاريخ الأمس"}),
                FieldSpec("time", {"en": "Time", "ar": "الوقت"}, "time", True,
                          sample={"en": "10:30", "ar": "10:30"}),
                FieldSpec("duration_minutes", {"en": "Duration (minutes)", "ar": "المدة (بالدقائق)"}, "integer", True,
                          default=30, sample={"en": "30", "ar": "30"},
                          validation={"min_value": 15, "max_value": 240},
                          invalid={"en": "the value 300", "ar": "القيمة 300"}),
                FieldSpec("status", {"en": "Status", "ar": "الحالة"}, "enum", True,
                          sample={"en": "scheduled", "ar": "محجوز"},
                          enum_values={"en": ["scheduled", "completed", "cancelled"],
                                       "ar": ["محجوز", "مكتمل", "ملغى"]},
                          default_index=0),
                FieldSpec("notes", {"en": "Notes", "ar": "ملاحظات"}, "text", False,
                          sample={"en": "First visit", "ar": "الزيارة الأولى"},
                          validation={"max_length": 500},
                          invalid={"en": "a text of 501 characters", "ar": "نصاً من 501 حرف"}),
            ],
            list_fields=["client_name", "date", "time", "service", "status"],
            search_fields=["client_name", "client_phone"],
            filter_fields=["status", "service", "date"],
            sort_field="date",
        )
    ],
    extra_rules=[
        ExtraRule(
            entity="Appointment",
            requirement={
                "en": "The system shall prevent saving an Appointment whose date and time are identical to another Appointment that is not cancelled.",
                "ar": "يجب أن يمنع النظام حفظ موعد له نفس التاريخ والوقت لموعد آخر غير ملغى.",
            },
            given={"en": "a scheduled Appointment exists on a date 3 days from today at 10:30",
                   "ar": "يوجد موعد محجوز بتاريخ بعد 3 أيام من اليوم الساعة 10:30"},
            when={"en": "the user saves a new Appointment for the same date at 10:30",
                  "ar": "يحفظ المستخدم موعداً جديداً بنفس التاريخ الساعة 10:30"},
            then={"en": "the new Appointment is not saved and the message \"This time slot is already booked\" is shown",
                  "ar": "لا يُحفظ الموعد الجديد وتظهر رسالة \"هذا الوقت محجوز مسبقاً\""},
        ),
    ],
    assumptions={
        "en": ["There is a single provider, so only one Appointment can occupy a date and time.",
               "Working hours are not enforced in the MVP."],
        "ar": ["يوجد مقدم خدمة واحد، لذا لا يمكن حجز أكثر من موعد في نفس التاريخ والوقت.",
               "لا يتم فرض ساعات العمل في النسخة الأولى."],
    },
    optional_questions=[
        {"en": "Do you need to manage several staff members or rooms with separate schedules?",
         "ar": "هل تحتاج إلى إدارة عدة موظفين أو غرف لكل منها جدول مستقل؟",
         "reason_en": "Multiple providers would add a Staff entity and change the double-booking rule.",
         "reason_ar": "تعدد مقدمي الخدمة يضيف كيان الموظفين ويغير قاعدة منع التعارض.",
         "default_en": "One provider only.", "default_ar": "مقدم خدمة واحد فقط."},
    ],
)

DOMAINS: Tuple[DomainSpec, ...] = (TASK_MANAGER, INVENTORY_MANAGER, APPOINTMENT_BOOKING)

COMMON_ASSUMPTIONS = {
    "en": ["The app is used by one person in one browser; data is stored in localStorage.",
           "Every record automatically gets id, created_at and updated_at system fields."],
    "ar": ["يستخدم التطبيق شخص واحد في متصفح واحد؛ وتُحفظ البيانات في localStorage.",
           "يحصل كل سجل تلقائياً على حقول النظام id و created_at و updated_at."],
}


# --------------------------------------------------------------------------------------
# Text templates
# --------------------------------------------------------------------------------------

T = {
    "fr_create": {"en": "The system shall allow the user to create a {label} by entering: {fields}.",
                  "ar": "يجب أن يسمح النظام للمستخدم بإنشاء {label} بإدخال: {fields}."},
    "fr_read": {"en": "The system shall display all {plural} in a list showing {columns}, sorted by {sort}{extras}.",
                "ar": "يجب أن يعرض النظام جميع {plural} في قائمة تظهر {columns} مرتبة حسب {sort}{extras}."},
    "fr_read_search": {"en": ", with search by {fields}", "ar": " مع البحث حسب {fields}"},
    "fr_read_filter": {"en": " and filters by {fields}", "ar": " والتصفية حسب {fields}"},
    "fr_update": {"en": "The system shall allow the user to edit any field of an existing {label} and save the changes.",
                  "ar": "يجب أن يسمح النظام للمستخدم بتعديل أي حقل في سجل موجود من {plural} وحفظ التعديلات."},
    "fr_delete": {"en": "The system shall allow the user to delete a {label} after confirming the action in a confirmation dialog.",
                  "ar": "يجب أن يسمح النظام للمستخدم بحذف {label} بعد تأكيد العملية في نافذة تأكيد."},
    "fr_validation": {"en": "The system shall reject saving a {label} unless: {rules}.",
                      "ar": "يجب أن يرفض النظام حفظ {label} ما لم: {rules}."},
    "fr_persist": {"en": "The system shall save all records in browser localStorage so they remain after the page is reloaded.",
                   "ar": "يجب أن يحفظ النظام جميع السجلات في localStorage في المتصفح بحيث تبقى بعد إعادة تحميل الصفحة."},
    "story": {
        "create": {"en": ("add a new {label}", "I can keep a record of it"),
                   "ar": ("أضيف سجلاً جديداً إلى {plural}", "أحتفظ بالبيانات في مكان واحد")},
        "read": {"en": ("view and search the list of {plural}", "I can find the record I need"),
                 "ar": ("أعرض قائمة {plural} وأبحث فيها", "أجد السجل الذي أحتاجه")},
        "update": {"en": ("edit an existing {label}", "its information stays correct"),
                   "ar": ("أعدّل سجلاً موجوداً في {plural}", "تبقى البيانات صحيحة ومحدّثة")},
        "delete": {"en": ("delete a {label} I no longer need", "the list only contains relevant records"),
                   "ar": ("أحذف سجلاً لم أعد أحتاجه من {plural}", "تحتوي القائمة على السجلات المهمة فقط")},
    },
}

RULE_TEXT = {
    "required": {"en": "{label} is filled in", "ar": "يُدخل {label}"},
    "min_length": {"en": "{label} has at least {v} characters", "ar": "يحتوي {label} على {v} أحرف على الأقل"},
    "max_length": {"en": "{label} has at most {v} characters", "ar": "لا يتجاوز {label} {v} حرفاً"},
    "min_value": {"en": "{label} is at least {v}", "ar": "لا تقل قيمة {label} عن {v}"},
    "max_value": {"en": "{label} is at most {v}", "ar": "لا تزيد قيمة {label} عن {v}"},
    "pattern": {"en": "{label} matches the pattern {v}", "ar": "يطابق {label} النمط {v}"},
    "date_constraint": {"en": "{label} is today or later", "ar": "يكون {label} اليوم أو بعده"},
    "unique": {"en": "{label} is unique", "ar": "يكون {label} غير مكرر"},
}

AC = {
    "create": {
        "en": ("the {plural} list is open with N records",
               "the user fills in {values} and clicks \"Save\"",
               "a {label} named \"{display}\" appears in the list and the list shows N + 1 records"),
        "ar": ("قائمة {plural} مفتوحة وتحتوي على N سجل",
               "يُدخل المستخدم {values} ويضغط \"حفظ\"",
               "يظهر سجل جديد باسم \"{display}\" في قائمة {plural} ويصبح عدد السجلات N + 1"),
    },
    "required": {
        "en": ("the create {label} form is open",
               "the user leaves all fields empty and clicks \"Save\"",
               "no {label} is saved and an error message is shown next to each required field: {fields}"),
        "ar": ("نموذج الإضافة في {plural} مفتوح",
               "يترك المستخدم جميع الحقول فارغة ويضغط \"حفظ\"",
               "لا يُحفظ أي سجل وتظهر رسالة خطأ بجانب كل حقل إلزامي: {fields}"),
    },
    "invalid": {
        "en": ("the create {label} form is open and all other fields are valid",
               "the user enters {invalid} in \"{field}\" and clicks \"Save\"",
               "the {label} is not saved and an error message is shown next to \"{field}\""),
        "ar": ("نموذج الإضافة في {plural} مفتوح وجميع الحقول الأخرى صحيحة",
               "يُدخل المستخدم {invalid} في \"{field}\" ويضغط \"حفظ\"",
               "لا يُحفظ السجل وتظهر رسالة خطأ بجانب \"{field}\""),
    },
    "unique": {
        "en": ("a {label} with {field} \"{value}\" already exists",
               "the user creates another {label} with {field} \"{value}\"",
               "the new {label} is not saved and an error message says the {field} is already used"),
        "ar": ("يوجد في {plural} سجل قيمة \"{field}\" فيه \"{value}\"",
               "يضيف المستخدم سجلاً آخر بالقيمة \"{value}\" في \"{field}\"",
               "لا يُحفظ السجل الجديد وتظهر رسالة خطأ بأن قيمة \"{field}\" مستخدمة مسبقاً"),
    },
    "persist": {
        "en": ("a {label} named \"{display}\" was created",
               "the user reloads the page",
               "\"{display}\" is still shown in the {plural} list with the same values"),
        "ar": ("تمت إضافة سجل باسم \"{display}\" إلى {plural}",
               "يعيد المستخدم تحميل الصفحة",
               "يبقى \"{display}\" ظاهراً في قائمة {plural} بنفس القيم"),
    },
    "read": {
        "en": ("3 {plural} have been created",
               "the user opens the {plural} list",
               "exactly 3 rows are shown, each with the columns {columns}"),
        "ar": ("تمت إضافة 3 سجلات إلى {plural}",
               "يفتح المستخدم قائمة {plural}",
               "تظهر 3 صفوف بالضبط، يحتوي كل منها على الأعمدة {columns}"),
    },
    "search": {
        "en": ("{plural} named \"{display}\" and \"Other record\" exist",
               "the user types \"{display}\" in the search box",
               "only the {label} \"{display}\" is shown in the list"),
        "ar": ("يوجد في {plural} سجلان باسم \"{display}\" و\"سجل آخر\"",
               "يكتب المستخدم \"{display}\" في مربع البحث",
               "يظهر السجل \"{display}\" فقط في القائمة"),
    },
    "empty": {
        "en": ("no {plural} exist", "the user opens the {plural} list",
               "an empty-state message is shown instead of the list"),
        "ar": ("لا توجد سجلات في {plural}", "يفتح المستخدم قائمة {plural}",
               "تظهر رسالة تفيد بعدم وجود سجلات بدلاً من القائمة"),
    },
    "update": {
        "en": ("a {label} named \"{display}\" exists",
               "the user changes {field} to \"{display} (edited)\", clicks \"Save\" and reloads the page",
               "the list shows \"{display} (edited)\" and no longer shows \"{display}\""),
        "ar": ("يوجد في {plural} سجل باسم \"{display}\"",
               "يغير المستخدم {field} إلى \"{display} (معدل)\" ويضغط \"حفظ\" ثم يعيد تحميل الصفحة",
               "تعرض القائمة \"{display} (معدل)\" ولا تعرض \"{display}\""),
    },
    "update_invalid": {
        "en": ("a {label} named \"{display}\" exists",
               "the user clears {field} in the edit form and clicks \"Save\"",
               "the change is not saved, an error message is shown and the list still shows \"{display}\""),
        "ar": ("يوجد في {plural} سجل باسم \"{display}\"",
               "يمسح المستخدم {field} في نموذج التعديل ويضغط \"حفظ\"",
               "لا يُحفظ التعديل وتظهر رسالة خطأ ويبقى \"{display}\" في القائمة"),
    },
    "delete": {
        "en": ("a {label} named \"{display}\" exists and the list shows N records",
               "the user clicks \"Delete\" on it and confirms",
               "\"{display}\" is removed from the list, the list shows N - 1 records, and it is still absent after reloading the page"),
        "ar": ("يوجد في {plural} سجل باسم \"{display}\" وتعرض القائمة N سجل",
               "يضغط المستخدم \"حذف\" عليه ثم يؤكد",
               "يُزال \"{display}\" من القائمة ويصبح العدد N - 1 ويبقى غير موجود بعد إعادة تحميل الصفحة"),
    },
    "delete_cancel": {
        "en": ("a {label} named \"{display}\" exists",
               "the user clicks \"Delete\" on it and cancels the confirmation",
               "\"{display}\" is still shown in the list"),
        "ar": ("يوجد في {plural} سجل باسم \"{display}\"",
               "يضغط المستخدم \"حذف\" عليه ثم يلغي التأكيد",
               "يبقى \"{display}\" ظاهراً في القائمة"),
    },
}

SEP = {"en": ", ", "ar": "، "}


# --------------------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------------------

def _match_domain(text: str) -> Optional[DomainSpec]:
    lowered = text.lower()
    best, best_hits = None, 0
    for domain in DOMAINS:
        hits = sum(1 for k in domain.keywords_en if _has_word(lowered, k))
        hits += sum(1 for k in domain.keywords_ar if k in text)
        if hits > best_hits:
            best, best_hits = domain, hits
    return best


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


class _Builder:
    def __init__(self, lang: str):
        self.lang = lang
        self.frs: List[dict] = []
        self.stories: List[dict] = []
        self.acs: List[dict] = []

    def fr(self, entity: Optional[str], category: str, description: str) -> str:
        rid = f"FR-{len(self.frs) + 1}"
        self.frs.append({"id": rid, "entity": entity, "category": category,
                         "description": description, "priority": "must"})
        return rid

    def story(self, role: str, goal: str, benefit: str, entity: str, op: str, reqs: List[str]) -> str:
        sid = f"US-{len(self.stories) + 1}"
        self.stories.append({"id": sid, "role": role, "goal": goal, "benefit": benefit,
                             "entity": entity, "operation": op, "requirement_ids": reqs})
        return sid

    def ac(self, story_id: str, category: str, triple: Tuple[str, str, str], **fmt: Any) -> None:
        given, when, then = (part.format(**fmt) for part in triple)
        self.acs.append({"id": f"AC-{len(self.acs) + 1}", "story_id": story_id, "category": category,
                         "given": given, "when": when, "then": then})


def _field_json(f: FieldSpec, lang: str) -> dict:
    out: Dict[str, Any] = {
        "name": f.name, "label": f.label[lang], "type": f.type,
        "required": f.required, "unique": f.unique, "validation": f.validation,
    }
    if f.enum_values:
        out["enum_values"] = f.enum_values[lang]
        if f.default_index is not None:
            out["default"] = f.enum_values[lang][f.default_index]
    if f.reference_entity:
        out["reference_entity"] = f.reference_entity
    if f.default is not None:
        out["default"] = f.default
    return out


def _entity_json(e: EntitySpec, lang: str) -> dict:
    return {
        "name": e.name, "label": e.label[lang], "plural_label": e.plural[lang],
        "description": e.description[lang], "display_field": e.display_field,
        "fields": [_field_json(f, lang) for f in e.fields],
        "crud": {
            "create": {"enabled": True, "details": ""},
            "read": {"enabled": True, "details": "", "list_fields": e.list_fields,
                     "search_fields": e.search_fields, "filter_fields": e.filter_fields,
                     "sort_field": e.sort_field, "sort_direction": e.sort_direction},
            "update": {"enabled": True, "details": ""},
            "delete": {"enabled": True, "details": "", "requires_confirmation": True},
        },
    }


def _labels(e: EntitySpec, names: List[str], lang: str) -> str:
    by_name = {f.name: f.label[lang] for f in e.fields}
    return SEP[lang].join(by_name[n] for n in names)


def _rules_text(e: EntitySpec, lang: str) -> str:
    parts = []
    for f in e.fields:
        label = f.label[lang]
        if f.required:
            parts.append(RULE_TEXT["required"][lang].format(label=label))
        if f.unique:
            parts.append(RULE_TEXT["unique"][lang].format(label=label))
        for key, value in f.validation.items():
            parts.append(RULE_TEXT[key][lang].format(label=label, v=value))
    return SEP[lang].join(parts)


def _build_entity(b: _Builder, domain: DomainSpec, e: EntitySpec) -> None:
    lang = b.lang
    label, plural = e.label[lang], e.plural[lang]
    display_f = next(f for f in e.fields if f.name == e.display_field)
    display = display_f.sample[lang]
    role = domain.role[lang]

    fr_create = b.fr(e.name, "create", T["fr_create"][lang].format(
        label=label, fields=SEP[lang].join(f.label[lang] for f in e.fields)))
    extras = ""
    if e.search_fields:
        extras += T["fr_read_search"][lang].format(fields=_labels(e, e.search_fields, lang))
    if e.filter_fields:
        extras += T["fr_read_filter"][lang].format(fields=_labels(e, e.filter_fields, lang))
    fr_read = b.fr(e.name, "read", T["fr_read"][lang].format(
        plural=plural, columns=_labels(e, e.list_fields, lang),
        sort=_labels(e, [e.sort_field], lang), extras=extras))
    fr_update = b.fr(e.name, "update", T["fr_update"][lang].format(label=label, plural=plural))
    fr_delete = b.fr(e.name, "delete", T["fr_delete"][lang].format(label=label))
    fr_valid = b.fr(e.name, "validation", T["fr_validation"][lang].format(label=label, rules=_rules_text(e, lang)))
    extra_frs = [(rule, b.fr(e.name, "validation", rule.requirement[lang]))
                 for rule in domain.extra_rules if rule.entity == e.name]

    def story(op: str, reqs: List[str]) -> str:
        goal, benefit = T["story"][op][lang]
        return b.story(role, goal.format(label=label, plural=plural), benefit, e.name, op, reqs)

    base = {"label": label, "plural": plural, "display": display, "field": display_f.label[lang]}

    # Create
    s = story("create", [fr_create, fr_valid] + [rid for _, rid in extra_frs])
    required = [f for f in e.fields if f.required]
    values = SEP[lang].join(f"{f.label[lang]} = \"{f.sample[lang]}\"" for f in required)
    b.ac(s, "create", AC["create"][lang], **base, values=values)
    b.ac(s, "validation", AC["required"][lang], **{**base, "fields": SEP[lang].join(f.label[lang] for f in required)})
    for f in e.fields:
        if f.invalid:
            b.ac(s, "validation", AC["invalid"][lang], **{**base, "invalid": f.invalid[lang], "field": f.label[lang]})
        if f.unique:
            b.ac(s, "validation", AC["unique"][lang], **{**base, "field": f.label[lang], "value": f.sample[lang]})
    for rule, _ in extra_frs:
        b.ac(s, "validation", (rule.given[lang], rule.when[lang], rule.then[lang]))
    b.ac(s, "persistence", AC["persist"][lang], **base)

    # Read
    s = story("read", [fr_read])
    b.ac(s, "read", AC["read"][lang], **base, columns=_labels(e, e.list_fields, lang))
    b.ac(s, "read", AC["empty"][lang], **base)
    if e.search_fields:
        b.ac(s, "read", AC["search"][lang], **base)

    # Update
    s = story("update", [fr_update, fr_valid])
    b.ac(s, "update", AC["update"][lang], **base)
    b.ac(s, "validation", AC["update_invalid"][lang], **base)

    # Delete
    s = story("delete", [fr_delete])
    b.ac(s, "delete", AC["delete"][lang], **base)
    b.ac(s, "delete", AC["delete_cancel"][lang], **base)


def _ready_document(domain: DomainSpec, idea: str, lang: str, out_of_scope: List[dict]) -> dict:
    b = _Builder(lang)
    for e in domain.entities:
        _build_entity(b, domain, e)
    persist_id = b.fr(None, "persistence", T["fr_persist"][lang])
    # Persistence is verified through the create story's persistence criterion.
    b.stories[0]["requirement_ids"].append(persist_id)

    questions = []
    for i, q in enumerate(domain.optional_questions, start=1):
        questions.append({"id": f"Q-{i}", "question": q[lang], "reason": q[f"reason_{lang}"],
                          "blocking": False, "options": [], "suggested_default": q[f"default_{lang}"]})

    return {
        "schema_version": "0.1.0-proposal",
        "status": "ready_for_review",
        "language": lang,
        "source_idea": idea,
        "app": {"name": domain.app_name[lang], "description": domain.description[lang],
                "target_users": domain.target_users[lang]},
        "entities": [_entity_json(e, lang) for e in domain.entities],
        "functional_requirements": b.frs,
        "user_stories": b.stories,
        "acceptance_criteria": b.acs,
        "clarification_questions": questions,
        "assumptions": COMMON_ASSUMPTIONS[lang] + domain.assumptions.get(lang, []),
        "out_of_scope": out_of_scope,
    }


_CLARIFY = {
    "en": {
        "name": "Untitled CRUD app",
        "description": "Application idea that still needs clarification: {idea}",
        "q1": "What kind of records do you want to manage (for example tasks, products, appointments, customers)?",
        "r1": "The main entity of the app cannot be identified from the idea.",
        "q2": "What information should be stored for each record (for example name, date, quantity, status)?",
        "r2": "Fields and their types are needed to build forms and validation.",
        "q3": "Who will use the app?",
        "r3": "Helps write user stories for the right role.",
        "d3": "A single person managing their own data.",
        "opts": ["Tasks", "Products / inventory", "Appointments", "Something else"],
        "reject_q": "Would a simple web app that records and manages the related data (create, view, edit, delete) be useful instead?",
        "reject_r": "The requested features are outside the CRUD MVP scope.",
        "reject_desc": "Requested application is outside the CRUD MVP scope: {idea}",
    },
    "ar": {
        "name": "تطبيق CRUD بدون اسم",
        "description": "فكرة تطبيق ما زالت بحاجة إلى توضيح: {idea}",
        "q1": "ما نوع السجلات التي تريد إدارتها (مثل المهام أو المنتجات أو المواعيد أو العملاء)؟",
        "r1": "لا يمكن تحديد الكيان الرئيسي للتطبيق من الفكرة.",
        "q2": "ما المعلومات التي يجب حفظها لكل سجل (مثل الاسم أو التاريخ أو الكمية أو الحالة)؟",
        "r2": "نحتاج إلى الحقول وأنواعها لبناء النماذج وقواعد التحقق.",
        "q3": "من سيستخدم التطبيق؟",
        "r3": "يساعد في كتابة قصص المستخدم للدور المناسب.",
        "d3": "شخص واحد يدير بياناته الخاصة.",
        "opts": ["المهام", "المنتجات / المخزون", "المواعيد", "شيء آخر"],
        "reject_q": "هل يفيدك بدلاً من ذلك تطبيق ويب بسيط لتسجيل البيانات المرتبطة وإدارتها (إضافة، عرض، تعديل، حذف)؟",
        "reject_r": "الميزات المطلوبة خارج نطاق النسخة الأولى (CRUD).",
        "reject_desc": "التطبيق المطلوب خارج نطاق النسخة الأولى (CRUD): {idea}",
    },
}


def _clarification_document(idea: str, lang: str, out_of_scope: List[dict]) -> dict:
    c = _CLARIFY[lang]
    return {
        "schema_version": "0.1.0-proposal",
        "status": "needs_clarification",
        "language": lang,
        "source_idea": idea,
        "app": {"name": c["name"], "description": c["description"].format(idea=idea), "target_users": []},
        "clarification_questions": [
            {"id": "Q-1", "question": c["q1"], "reason": c["r1"], "blocking": True, "options": c["opts"]},
            {"id": "Q-2", "question": c["q2"], "reason": c["r2"], "blocking": True, "options": []},
            {"id": "Q-3", "question": c["q3"], "reason": c["r3"], "blocking": False, "options": [],
             "suggested_default": c["d3"]},
        ],
        "assumptions": COMMON_ASSUMPTIONS[lang],
        "out_of_scope": out_of_scope,
    }


def _rejected_document(idea: str, lang: str, out_of_scope: List[dict]) -> dict:
    c = _CLARIFY[lang]
    return {
        "schema_version": "0.1.0-proposal",
        "status": "rejected_out_of_scope",
        "language": lang,
        "source_idea": idea,
        "app": {"name": c["name"], "description": c["reject_desc"].format(idea=idea), "target_users": []},
        "clarification_questions": [
            {"id": "Q-1", "question": c["reject_q"], "reason": c["reject_r"], "blocking": False, "options": []},
        ],
        "out_of_scope": out_of_scope,
    }


def mock_generate(idea: str, language: str, answers: Optional[Dict[str, str]] = None) -> str:
    """Return a raw JSON string, exactly like an LLM response would be."""
    text = idea + "\n" + "\n".join((answers or {}).values())
    out_of_scope = [item.model_dump() for item in detect_out_of_scope(text, language)]
    domain = _match_domain(text)
    if domain is not None:
        doc = _ready_document(domain, idea, language, out_of_scope)
    elif out_of_scope:
        doc = _rejected_document(idea, language, out_of_scope)
    else:
        doc = _clarification_document(idea, language, out_of_scope)
    return json.dumps(doc, ensure_ascii=False, indent=2)
