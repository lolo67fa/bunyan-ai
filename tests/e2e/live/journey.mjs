// One full BUNYAN journey through the real React UI and backend, as a user would do it:
// idea -> Business Analyst -> review -> request a change -> revised requirements
// -> approve -> Architect, Developer, QA, Project Manager -> delivery and ZIP.
//
// Used by .github/workflows/ba-live-journey.yml. It only clicks and reads; the backend
// decides which model runs (BA_MODE). Writes screenshots and journey.json to --out.
//
//   FRONTEND_URL=http://127.0.0.1:4173 API_URL=http://127.0.0.1:8000 \
//   IDEA="..." FEEDBACK="..." node tests/e2e/live/journey.mjs --out live-journey

import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { chromium } from '@playwright/test';

const FRONTEND = process.env.FRONTEND_URL ?? 'http://127.0.0.1:4173';
const API = process.env.API_URL ?? 'http://127.0.0.1:8000';
const IDEA = process.env.IDEA ?? 'أبغى موقع لإدارة المخزون أقدر أضيف فيه المنتجات وأعدل كمياتها وأسعارها وأحذف المنتجات.';
const FEEDBACK = process.env.FEEDBACK ?? 'أضف حقل رقم جوال المورد';
const OUT = process.argv.includes('--out') ? process.argv[process.argv.indexOf('--out') + 1] : 'live-journey';
const ANALYSIS_TIMEOUT = 12 * 60_000; // a real model can take minutes
const BUILD_TIMEOUT = 10 * 60_000;

mkdirSync(OUT, { recursive: true });
const report = { idea: IDEA, feedback: FEEDBACK, steps: [], result: 'failed', checks: {} };
const started = Date.now();
const step = (name, extra = {}) => {
  report.steps.push({ name, at_seconds: Math.round((Date.now() - started) / 1000), ...extra });
  console.log(`[${Math.round((Date.now() - started) / 1000)}s] ${name}`, Object.keys(extra).length ? JSON.stringify(extra) : '');
};
const api = async (path) => {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`GET ${path}: ${res.status}`);
  return res.headers.get('content-type')?.includes('json') ? res.json() : res.text();
};
async function waitFor(id, ready, what, timeout) {
  const end = Date.now() + timeout;
  for (;;) {
    const p = await api(`/projects/${id}`);
    if (ready(p)) return p;
    if (Date.now() > end) throw new Error(`timed out waiting for ${what}; status is ${p.status}`);
    await new Promise((r) => setTimeout(r, 3000));
  }
}
const waitForStatus = (id, done, timeout) => waitFor(id, (p) => done.includes(p.status), done.join('|'), timeout);
const STOPPED = ['awaiting_approval', 'awaiting_clarification', 'rejected', 'failed'];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, locale: 'ar' });
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
const shot = (name) => page.screenshot({ path: join(OUT, `${name}.png`), fullPage: true });
let id = null;

try {
  // 1. The idea
  await page.goto(`${FRONTEND}/#/new`);
  await page.locator('textarea').first().fill(IDEA);
  await page.getByRole('button', { name: 'حلّل فكرتي' }).click();
  await page.waitForURL(/#\/projects\/[0-9a-f-]{36}/, { timeout: 30_000 });
  id = page.url().match(/projects\/([0-9a-f-]{36})/)[1];
  report.project_id = id;
  step('idea submitted', { status: (await api(`/projects/${id}`)).status });

  // 2. Business Analyst
  let project = await waitForStatus(id, STOPPED, ANALYSIS_TIMEOUT);
  step('analysis finished', { status: project.status, seconds: project.analysis?.seconds, mode: project.analysis?.mode });
  report.checks.analysis_mode_llm = project.analysis?.mode === 'llm';
  report.first_requirements = project.requirements;
  await page.reload();
  await shot('1-requirements');
  if (project.status !== 'awaiting_approval') throw new Error(`analysis ended in ${project.status}: ${JSON.stringify(project.error)}`);
  report.checks.single_entity = project.requirements.entities.length === 1;
  report.checks.compatible = project.compatibility?.supported === true;

  // 3. Request a change
  await page.getByRole('button', { name: 'طلب تعديل' }).first().click();
  await page.getByLabel('التعديلات المطلوبة').fill(FEEDBACK);
  await page.getByRole('button', { name: 'إرسال', exact: true }).click();
  step('change requested');
  // Wait for this revision to finish, not just for any review status (the request may not have arrived yet).
  project = await waitFor(
    id,
    (p) => p.analysis?.kind === 'feedback' && p.analysis?.outcome && STOPPED.includes(p.status),
    'the revision',
    ANALYSIS_TIMEOUT,
  );
  step('revision finished', { status: project.status, seconds: project.analysis?.seconds, changed: project.revision?.changed });
  report.revision = project.revision ?? null;
  report.revised_requirements = project.requirements;
  report.error_after_revision = project.error;
  await page.reload();
  const notice = page.locator('[data-testid="revision-applied"], [data-testid="revision-unchanged"], [data-testid="analysis-error"]').first();
  await notice.waitFor({ timeout: 30_000 });
  report.revision_notice = { testid: await notice.getAttribute('data-testid'), text: await notice.innerText() };
  await shot('2-revised-requirements');
  report.checks.revision_shown_honestly =
    (project.revision?.changed === true && report.revision_notice.testid === 'revision-applied') ||
    (project.revision?.changed === false && report.revision_notice.testid === 'revision-unchanged');
  report.checks.feedback_applied = (project.revision?.added_fields ?? []).length > 0;
  if (project.status !== 'awaiting_approval') throw new Error(`revision ended in ${project.status}`);

  // 4. Approve and build
  await page.getByRole('button', { name: 'الموافقة على المتطلبات' }).first().click();
  step('approved');
  project = await waitForStatus(id, ['completed', 'failed'], BUILD_TIMEOUT);
  step('pipeline finished', { status: project.status, qa: project.qa?.status, metrics: project.metrics, error: project.error });
  await page.reload();
  await page.locator('[data-testid="delivery"], [data-testid="failed"]').first().waitFor({ timeout: 30_000 });
  await shot('3-delivery');
  report.final = { status: project.status, qa: project.qa, metrics: project.metrics, error: project.error };

  // 5. What was delivered
  const zip = await fetch(`${API}/projects/${id}/download`);
  report.zip = { status: zip.status, type: zip.headers.get('content-type'), bytes: (await zip.arrayBuffer()).byteLength };
  if (project.status === 'completed') {
    const architecture = await api(`/projects/${id}/artifacts/architecture.json`);
    report.architecture_fields = architecture.entity.fields.map((f) => `${f.name}:${f.input}`);
    writeFileSync(join(OUT, 'test_report.json'), JSON.stringify(await api(`/projects/${id}/artifacts/test_report.json`), null, 2));
    writeFileSync(join(OUT, 'project_plan.md'), await api(`/projects/${id}/artifacts/project_plan.md`));
    const added = (project.revision?.added_fields ?? []).map((f) => f.field);
    report.checks.added_field_reaches_the_app = added.length > 0 && added.every((n) => architecture.entity.fields.some((f) => f.name === n));
  }
  report.checks.completed = project.status === 'completed';
  report.checks.qa_passed = project.qa?.status === 'passed';
  report.checks.zip_ok = report.zip.status === 200;
  report.checks.no_page_errors = errors.length === 0;
  report.result = report.checks.completed && report.checks.qa_passed && report.checks.zip_ok ? 'passed' : 'failed';
} catch (e) {
  report.error = String(e?.message ?? e);
  step('stopped', { error: report.error });
  await shot('error').catch(() => {});
  if (id) report.project_at_stop = await api(`/projects/${id}`).catch(() => null);
} finally {
  report.page_errors = errors;
  report.duration_seconds = Math.round((Date.now() - started) / 1000);
  writeFileSync(join(OUT, 'journey.json'), JSON.stringify(report, null, 2));
  await browser.close();
}
console.log(`journey: ${report.result}`, JSON.stringify(report.checks));
process.exit(report.result === 'passed' ? 0 : 1);
