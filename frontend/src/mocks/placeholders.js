// PLACEHOLDERS for artifacts whose contracts are not agreed yet.
// Only requirements.json is real (Ghala's samples). Everything here is a stand-in
// so the screens can be built, and must be replaced once each owner shares a sample:
//   architecture.json  → Naifah    test_report.json → Sara
//   generated app      → Yara      project_plan.md / risks.md → Jood (Project Manager agent)

const MOCK_NOTE = 'MOCK placeholder — not an agreed contract';

export function mockArchitecture(req) {
  return {
    _mock: true,
    _note: `${MOCK_NOTE} (owner: Naifah)`,
    app_name: req.app.name,
    language: req.language,
    direction: req.language === 'ar' ? 'rtl' : 'ltr',
    screens: req.entities.map((e) => ({ entity: e.name, views: ['list', 'form'] })),
    storage: req.entities.map((e) => ({ entity: e.name, key: `bunyan.${e.name.toLowerCase()}` })),
  };
}

// Same 8 checks, ids, descriptions and categories as Sara's suite
// (PR #7: tests/e2e/lib/checks.js).
const CHECKS = [
  { id: 'create_item', categories: ['create'], description: 'Add a record through the form; it appears in the list and the row count grows by one.' },
  { id: 'list_items', categories: ['read'], description: 'Three records are listed, each row showing every column from crud.read.list_fields.' },
  { id: 'edit_item', categories: ['update'], description: 'Edit opens a pre-filled form; after saving, the list shows the new value and not the old one.' },
  { id: 'delete_item', categories: ['delete'], description: 'Cancelling the delete keeps the record; confirming removes only that record.' },
  { id: 'persist_after_refresh', categories: ['persistence'], description: 'A saved record is still listed after the page is reloaded (localStorage).' },
  { id: 'reject_incomplete_input', categories: ['validation'], description: 'Saving with required fields empty does not add a record, before or after reload.' },
  { id: 'empty_state', categories: ['read'], description: 'With no records the empty-state message is shown; it disappears after the first record.' },
  { id: 'error_message_visible', categories: ['validation'], description: 'Saving with required fields empty shows a non-empty error next to each of those fields.' },
];

const FAILING_CHECK = 'persist_after_refresh';

/**
 * Mock test_report.json in Sara's contract shape (PR #7: tests/e2e/contract/TEST_REPORT.md,
 * schema 0.1.0-proposal). `attempt` is run.attempt: 0 = first run, 1–2 = re-test after repair.
 * `fail` makes FAILING_CHECK fail, to show the repair loop.
 */
export function mockTestReport(req, { attempt = 0, fail = false } = {}) {
  const entity = req.entities[0];
  const criteria = req.acceptance_criteria ?? [];
  const checks = CHECKS.map((c) => {
    const failed = fail && c.id === FAILING_CHECK;
    return {
      id: c.id,
      description: c.description,
      status: failed ? 'failed' : 'passed',
      duration_ms: 900,
      related_criteria: criteria.filter((a) => c.categories.includes(a.category)).map((a) => a.id),
      error: failed ? { message: 'record should survive a reload (MOCK)' } : null,
      skip_reason: null,
      evidence: { screenshot: null, trace: null },
    };
  });
  const passed = checks.filter((c) => c.status === 'passed').length;
  const failed = checks.length - passed;
  const now = new Date();
  const durationMs = checks.reduce((s, c) => s + c.duration_ms, 0);
  return {
    _mock: true,
    _note: `${MOCK_NOTE} (owner: Sara)`,
    schema_version: '0.1.0-proposal',
    generated_at: now.toISOString(),
    app: { name: req.app.name, language: req.language },
    entity: entity?.name ?? null,
    inputs: {
      requirements_path: 'requirements.json',
      requirements_schema_version: req.schema_version,
      app_dir: 'generated',
      is_harness_fixture: false,
    },
    run: {
      attempt,
      max_repair_attempts: 2,
      started_at: new Date(now.getTime() - durationMs).toISOString(),
      finished_at: now.toISOString(),
      duration_ms: durationMs,
      browser: 'chromium',
      playwright_version: null,
      runner_status: failed ? 'failed' : 'passed',
      blocked_reason: null,
    },
    summary: {
      total: checks.length,
      passed,
      failed,
      skipped: 0,
      not_run: 0,
      pass_rate: passed / checks.length,
      all_passed: failed === 0,
    },
    checks,
    defects: checks
      .filter((c) => c.status === 'failed')
      .map((c) => ({ check_id: c.id, message: c.error.message, evidence: c.evidence })),
    warnings: [],
  };
}

/**
 * The summary the backend puts in Project.metrics, built from Sara's report
 * (mapping from TEST_REPORT.md §4). run_time_seconds is the whole pipeline and
 * comes from the orchestrator, not from the QA report.
 */
export function metricsFromReport(report, runTimeSeconds) {
  return {
    pass_rate: report.summary.pass_rate,
    checks_passed: report.summary.passed,
    checks_total: report.summary.total,
    run_time_seconds: runTimeSeconds,
  };
}

// DRAFT output format for the Project Manager agent (Jood). Built only from data the
// other agents produced; the real agent writes the same sections in the same order.
export function mockProjectPlan(project) {
  const req = project.requirements;
  const m = project.metrics;
  const e = req.entities;
  const fields = e.reduce((n, x) => n + x.fields.length, 0);
  const done = project.status === 'completed';
  const st = (ok) => (ok ? 'مكتمل' : 'جارٍ');
  const outOf = req.out_of_scope.map((o) => o.feature);
  const repairs = project.repair_attempt ?? 0;
  return `# خطة المشروع: ${req.app.name}

## النطاق
${req.app.description}

- **يشمل:** ${e.map((x) => x.plural_label ?? x.label).join('، ')}: الإضافة والعرض والتعديل والحذف، مع البحث والترتيب والتحقق من الحقول.
- **لا يشمل:** ${outOf.length ? outOf.join('، ') : 'تعدد المستخدمين، المزامنة السحابية، التقارير'}.

## المراحل
| المرحلة | المسؤول | المخرج | الحالة |
|---|---|---|---|
| اعتماد المتطلبات | محلّل الأعمال وأنت | ${fields} حقول، ${req.functional_requirements.length} متطلبات، ${req.user_stories.length} قصص مستخدم | مكتمل |
| تصميم الهيكل | المهندس | نموذج البيانات والشاشات والتحقق | مكتمل |
| كتابة الكود | المطوّر | index.html · style.css · app.js | مكتمل |
| اختبار الجودة | مختبر الجودة | ${m ? `${m.checks_passed} من ${m.checks_total}` : '—'}${repairs ? ` بعد ${repairs === 1 ? 'إصلاح واحد' : 'إصلاحين'}` : ''} | ${st(Boolean(m))} |
| التسليم | مدير المشروع | ملف ZIP وهذه الخطة | ${st(done)} |
`;
}

export function mockRisks(project) {
  const req = project.requirements;
  const rows = [
    '| فقدان البيانات إذا مُسحت بيانات المتصفح | متوسط | عالٍ | رسالة توضيحية داخل التطبيق، والتصدير اليدوي مقترح لنسخة لاحقة. |',
    '| الحاجة للاستخدام من أكثر من جهاز | متوسط | متوسط | خارج نطاق هذه النسخة، ومذكور في المتطلبات. |',
  ];
  if ((project.repair_attempt ?? 0) > 0) {
    rows.push('| فحص فشل في التشغيل الأول | — | — | أُغلق: أصلحه المطوّر وتحقق منه الفحص في التشغيل التالي. |');
  }
  req.out_of_scope.slice(0, 2).forEach((o) => {
    rows.push(`| طلب ميزة مستبعدة: ${o.feature} | منخفض | متوسط | ${o.alternative ?? 'تُناقش في نسخة لاحقة.'} |`);
  });
  return `## المخاطر
| الخطر | الاحتمال | الأثر | المعالجة |
|---|---|---|---|
${rows.join('\n')}
`;
}

/** Stand-in preview of the generated app (Yara's Developer agent replaces this).
 *  Built from Naifah's architecture.json when a sample exists, otherwise from requirements. */
export function mockPreviewHtml(req, arch) {
  const lang = req.language === 'ar' ? 'ar' : 'en';
  const dir = lang === 'ar' ? 'rtl' : 'ltr';
  const entity = arch?.entity ?? req.entities[0];
  const fields = entity.fields;
  const listScreen = arch?.screens?.find((s) => s.type === 'list');
  const columns = listScreen?.components?.find((c) => c.type === 'table')?.columns
    ?? req.entities[0].crud?.read?.list_fields
    ?? fields.map((f) => f.name);
  const byName = Object.fromEntries(fields.map((f) => [f.name, f]));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const sample = (f, i) => {
    const opts = f.enum_values ?? f.options?.map((o) => o.label ?? o.value);
    if (opts?.length) return opts[i % opts.length];
    switch (f.type) {
      case 'integer': return [120, 3, 18, 42][i % 4];
      case 'decimal': return ['2.50', '12.00', '149.00', '38.50'][i % 4];
      case 'date': return ['2026-11-20', '2026-11-22', '2026-12-01', '2026-12-04'][i % 4];
      case 'time': return ['09:30', '11:00', '13:15', '16:45'][i % 4];
      case 'boolean': return i % 2 ? (lang === 'ar' ? 'لا' : 'No') : (lang === 'ar' ? 'نعم' : 'Yes');
      case 'phone': return ['0501234567', '0559876543', '0533344455', '0561112223'][i % 4];
      case 'email': return ['sara@example.com', 'ali@example.com', 'noor@example.com', 'omar@example.com'][i % 4];
      default:
        if (/sku|code|رمز/i.test(f.name + f.label)) return ['PEN-001', 'NB-014', 'EL-210', 'FD-077'][i % 4];
        return lang === 'ar'
          ? ['قلم حبر أزرق', 'دفتر A4', 'سماعة لاسلكية', 'قهوة عربية 500 غ'][i % 4]
          : ['Prepare weekly report', 'Call the supplier', 'Update price list', 'Review new orders'][i % 4];
    }
  };
  const rows = [0, 1, 2, 3]
    .map((i) => `<tr>${columns.map((c) => `<td>${esc(byName[c] ? sample(byName[c], i) : '')}</td>`).join('')}<td class="act"><button>${lang === 'ar' ? 'تعديل' : 'Edit'}</button><button class="del">${lang === 'ar' ? 'حذف' : 'Delete'}</button></td></tr>`)
    .join('');
  const inputs = fields
    .slice(0, 5)
    .map((f) => `<label>${esc(f.label)}${f.required ? ' *' : ''}<input placeholder="${esc(sample(f, 0))}"></label>`)
    .join('');
  const t = lang === 'ar'
    ? { add: 'إضافة', search: 'ابحث…', note: 'البيانات محفوظة في هذا المتصفح فقط.', count: `${rows ? 4 : 0} سجلات` }
    : { add: 'Add', search: 'Search…', note: 'Data is saved in this browser only.', count: '4 records' };
  return `<!doctype html><html lang="${lang}" dir="${dir}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(req.app.name)}</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Tahoma,sans-serif;background:#f6f8fb;color:#1f2937;font-size:14px}
.wrap{max-width:980px;margin:0 auto;padding:24px 16px}
header{display:flex;justify-content:space-between;align-items:baseline;border-bottom:3px solid #2563eb;padding-bottom:10px;margin-bottom:16px}
h1{font-size:20px;margin:0}.count{color:#6b7280;font-size:12px}
form{display:flex;flex-wrap:wrap;gap:10px;align-items:end;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:12px;margin-bottom:12px}
label{display:grid;gap:4px;font-size:12px;font-weight:600;flex:1 1 140px}
input{padding:8px;border:1px solid #d1d5db;border-radius:6px;font:inherit}
.add{background:#2563eb;color:#fff;border:0;border-radius:6px;padding:9px 18px;font:inherit;font-weight:600}
.search{width:100%;padding:8px;border:1px solid #d1d5db;border-radius:6px;margin-bottom:12px;font:inherit}
.tw{overflow-x:auto;background:#fff;border:1px solid #e5e7eb;border-radius:8px}
table{width:100%;border-collapse:collapse}th,td{padding:10px;text-align:start;border-bottom:1px solid #f0f1f3;white-space:nowrap}
th{font-size:12px;color:#6b7280;background:#f9fafb}.act{display:flex;gap:6px}
.act button{border:1px solid #d1d5db;background:#fff;border-radius:6px;padding:4px 10px;font:inherit;font-size:12px}
.act .del{color:#b42318;border-color:#f3c9c3}.note{color:#6b7280;font-size:12px;margin-top:10px}
</style></head><body><div class="wrap">
<header><h1>${esc(req.app.name)}</h1><span class="count">${t.count}</span></header>
<form>${inputs}<button class="add">${t.add}</button></form>
<input class="search" placeholder="${t.search}">
<div class="tw"><table><thead><tr>${columns.map((c) => `<th>${esc(byName[c]?.label ?? c)}</th>`).join('')}<th></th></tr></thead><tbody>${rows}</tbody></table></div>
<p class="note">${t.note}</p>
</div></body></html>`;
}
