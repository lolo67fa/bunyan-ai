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

// DRAFT output format for the Project Manager agent (Jood). Built from real run data only.
export function mockProjectPlan(project) {
  const req = project.requirements;
  const m = project.metrics;
  const entities = req.entities.map((e) => `${e.label} (${e.name})`).join('، ');
  const must = req.functional_requirements.filter((r) => r.priority === 'must').length;
  return `# خطة المشروع — ${req.app.name}

> مسودة شكل مخرجات وكيل مدير المشروع (MOCK)

## ملخص الحالة
- الحالة: ${project.status === 'completed' ? 'مكتمل' : project.status}
- الكيانات: ${entities}
- المتطلبات الوظيفية: ${req.functional_requirements.length} (منها ${must} إلزامية)
- نتيجة الاختبار: ${m ? `${Math.round(m.pass_rate * 100)}%` : 'غير متوفرة'}
- محاولات الإصلاح: ${project.repair_attempt ?? 0} من 2
- مدة التشغيل: ${m ? `${m.run_time_seconds} ثانية` : 'غير متوفرة'}

## المراحل
| المرحلة | المخرج | الحالة |
|---|---|---|
| تحليل المتطلبات | requirements.json | ✅ |
| تصميم الهيكلة | architecture.json | ✅ |
| توليد الكود | index.html · style.css · app.js | ✅ |
| الاختبار | test_report.json | ${m && m.pass_rate === 1 ? '✅' : '⚠️'} |
| التوثيق | project_plan.md · risks.md | ✅ |
`;
}

export function mockRisks(project) {
  const req = project.requirements;
  const lines = [
    '| # | الخطر | الأثر | المعالجة |',
    '|---|---|---|---|',
    '| R-1 | البيانات محفوظة في localStorage فقط | فقدها عند مسح المتصفح | بيانات تجريبية فقط حسب حدود المشروع |',
  ];
  req.out_of_scope.forEach((o, i) => {
    lines.push(`| R-${i + 2} | ميزة مستبعدة: ${o.feature} | ${o.reason} | ${o.alternative ?? 'مستبعدة'} |`);
  });
  return `# المخاطر — ${req.app.name}\n\n> مسودة (MOCK)\n\n${lines.join('\n')}\n`;
}

/** Stand-in preview. Yara's generated app replaces this. */
export function mockPreviewHtml(req) {
  const dir = req.language === 'ar' ? 'rtl' : 'ltr';
  const e = req.entities[0];
  const byName = Object.fromEntries(e.fields.map((f) => [f.name, f]));
  const cols = (e.crud?.read?.list_fields ?? e.fields.map((f) => f.name))
    .map((n) => `<th>${byName[n]?.label ?? n}</th>`)
    .join('');
  const inputs = e.fields
    .map(
      (f) =>
        `<label>${f.label}${f.required ? ' *' : ''}<input disabled placeholder="${f.type}"></label>`,
    )
    .join('');
  return `<!doctype html><html lang="${req.language}" dir="${dir}"><head><meta charset="utf-8">
<style>body{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#f7f7fb;color:#222}
.banner{background:#fff4d6;border:1px solid #f0d58a;padding:8px 12px;border-radius:8px;font-size:13px;margin-bottom:12px}
h1{font-size:20px;margin:0 0 12px}form{display:grid;gap:8px;background:#fff;padding:12px;border-radius:10px;margin-bottom:12px}
label{display:grid;gap:4px;font-size:13px}input{padding:8px;border:1px solid #ccc;border-radius:6px}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden}
th,td{padding:8px;border-bottom:1px solid #eee;text-align:start;font-size:13px}.empty{padding:16px;text-align:center;color:#777}</style>
</head><body><div class="banner">MOCK preview — the Developer agent's generated app will appear here.</div>
<h1>${req.app.name} — ${e.plural_label}</h1><form>${inputs}</form>
<table><thead><tr>${cols}</tr></thead></table><div class="empty">No records yet</div></body></html>`;
}
