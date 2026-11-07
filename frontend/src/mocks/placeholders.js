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

// The plan fixes "8 core checks" but their exact list is Sara's decision.
const CHECKS = [
  'create_item',
  'list_items',
  'edit_item',
  'delete_item',
  'persist_after_refresh',
  'reject_incomplete_input',
  'empty_state',
  'error_message_visible',
];

export function mockTestReport(req, { failFirstRun = false } = {}) {
  const checks = CHECKS.map((id) => ({
    id,
    passed: !(failFirstRun && id === 'persist_after_refresh'),
  }));
  const passed = checks.filter((c) => c.passed).length;
  return {
    _mock: true,
    _note: `${MOCK_NOTE} (owner: Sara)`,
    app_name: req.app.name,
    total: checks.length,
    passed,
    failed: checks.length - passed,
    pass_rate: passed / checks.length,
    checks,
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
