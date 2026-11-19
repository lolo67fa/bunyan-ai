// Arabic wording used across screens. Keep user-facing text here so the
// tone stays the same everywhere: short, plain, the user's own words.

export const STAGES = [
  { key: 'requirements', label: 'المتطلبات', agent: 'business_analyst' },
  { key: 'structure', label: 'الهيكل', agent: 'software_architect' },
  { key: 'development', label: 'التطوير', agent: 'developer' },
  { key: 'tests', label: 'الاختبار', agent: 'qa_tester' },
  { key: 'plan', label: 'الخطة', agent: 'project_manager' },
];

const STAGE_OF_STATUS = {
  created: 0, analyzing: 0, awaiting_clarification: 0, awaiting_approval: 0, rejected: 0,
  approved: 1, designing: 1, developing: 2, repairing: 2, testing: 3, documenting: 4, completed: 4,
};

/** Status text + tone for lists and headers. Tone maps to .status-{tone}. */
export function projectStatus(p) {
  switch (p.status) {
    case 'created':
    case 'analyzing':
      return { text: 'قيد التحليل', tone: 'working' };
    case 'awaiting_clarification':
      return { text: 'بانتظار إجاباتك', tone: 'waiting' };
    case 'awaiting_approval':
      return { text: 'بانتظار موافقتك', tone: 'waiting' };
    case 'completed':
      return { text: 'جاهز للتحميل', tone: 'done' };
    case 'rejected':
      return { text: 'خارج النطاق', tone: 'failed' };
    case 'failed':
      return { text: 'فشل', tone: 'failed' };
    default:
      return { text: 'قيد التنفيذ', tone: 'working' };
  }
}

/** "المتطلبات · 1 من 5" or "مكتمل · اجتاز 8 من 8 فحوصات" */
export function projectStage(p) {
  if (p.status === 'completed') {
    const m = p.metrics;
    return m ? `مكتمل · اجتاز ${m.checks_passed} من ${m.checks_total} فحوصات` : 'مكتمل';
  }
  const i = STAGE_OF_STATUS[p.status] ?? 0;
  return `${STAGES[i].label} · ${i + 1} من ${STAGES.length}`;
}

export function statusGroup(p) {
  if (['awaiting_clarification', 'awaiting_approval'].includes(p.status)) return 'waiting';
  if (p.status === 'completed') return 'done';
  if (['failed', 'rejected'].includes(p.status)) return 'stopped';
  return 'running';
}

export const FIELD_TYPES = {
  string: 'نص',
  text: 'نص طويل',
  integer: 'عدد صحيح',
  decimal: 'رقم عشري',
  boolean: 'نعم / لا',
  date: 'تاريخ',
  time: 'وقت',
  datetime: 'تاريخ ووقت',
  email: 'بريد إلكتروني',
  phone: 'رقم جوال',
  url: 'رابط',
  enum: 'قائمة',
  reference: 'ربط',
};

/** Rules column: "من 2 إلى 80 حرفاً · غير مكرر" */
export function fieldRules(f) {
  const v = f.validation ?? {};
  const out = [];
  if (v.min_length != null && v.max_length != null) out.push(`من ${v.min_length} إلى ${v.max_length} حرفاً`);
  else if (v.max_length != null) out.push(`حتى ${v.max_length} حرفاً`);
  else if (v.min_length != null) out.push(`${v.min_length} أحرف على الأقل`);
  if (v.min_value != null && v.max_value != null) out.push(`من ${v.min_value} إلى ${v.max_value}`);
  else if (v.min_value === 0) out.push('صفر أو أكثر');
  else if (v.min_value != null) out.push(`${v.min_value} أو أكثر`);
  else if (v.max_value != null) out.push(`حتى ${v.max_value}`);
  if (v.date_constraint === 'not_in_past') out.push('ليس في الماضي');
  if (v.date_constraint === 'not_in_future') out.push('ليس في المستقبل');
  if (f.unique) out.push('غير مكرر');
  const options = f.enum_values ?? f.options?.map((o) => o.label ?? o.value);
  if (options?.length) out.push(options.join('، '));
  if (f.type === 'reference' && f.reference_entity) out.push(`مرتبط بـ ${f.reference_entity}`);
  if (f.default != null && f.default !== '') out.push(`الافتراضي: ${f.default}`);
  return out.join(' · ');
}

/** QA checks: Arabic name and what each verifies (ids from Sara's suite). */
export function checkLabels(entityLabel = 'السجل') {
  const item = entityLabel;
  return {
    create_item: ['إضافة سجل', `يُضاف ${item} ويظهر في الجدول`],
    list_items: ['عرض السجلات', 'تظهر كل السجلات المحفوظة'],
    edit_item: ['تعديل سجل', 'تظهر القيمة الجديدة بعد الحفظ'],
    delete_item: ['حذف سجل', `يختفي ${item} بعد التأكيد`],
    persist_after_refresh: ['الحفظ بعد التحديث', 'تبقى البيانات بعد إعادة تحميل الصفحة'],
    reject_incomplete_input: ['الحقول المطلوبة', 'يرفض الحفظ إذا نقص حقل مطلوب'],
    empty_state: ['القائمة الفارغة', 'تظهر رسالة عند عدم وجود سجلات'],
    error_message_visible: ['ظهور رسائل الخطأ', 'الرسالة ظاهرة وقريبة من الحقل'],
  };
}

export const SCREEN_TYPES = { list: 'قائمة', form: 'نموذج' };

export const BEHAVIORS = {
  validate_before_save: 'التحقق من الحقول قبل الحفظ',
  check_unique_before_save: 'منع التكرار قبل الحفظ',
  prefill_form_on_edit: 'تعبئة النموذج بالقيم الحالية عند التعديل',
  load_on_start: 'تحميل البيانات عند فتح الصفحة',
};

export function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', { day: 'numeric', month: 'long' }).format(new Date(iso));
  } catch {
    return iso.slice(0, 10);
  }
}

export function formatDuration(ms) {
  const s = Math.max(0, Math.round(ms / 1000));
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, '0')}`;
}

export function slug(text = '') {
  return (text ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

/** File-safe project name: the app name if it is Latin, else "<entity>-manager" (e.g. category-manager). */
export function projectSlug(project) {
  const req = project?.requirements;
  return slug(req?.app?.name) || (req?.entities?.[0]?.name ? `${slug(req.entities[0].name)}-manager` : 'bunyan-app');
}
