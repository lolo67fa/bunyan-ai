// What the screens say about QA and repairs. Shapes follow backend/orchestrator/README.md.
// Runs with Node's built-in test runner: `npm test`.

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { hasGeneratedApp } from '../src/constants/stages.js';
import { projectStage } from '../src/lib/labels.js';
import { MSG } from '../src/lib/messages.js';
import { qaSummary, repairCount } from '../src/lib/qa.js';

const files = (...names) => names.map((name) => ({ name, available: true }));
const APP = ['requirements.json', 'architecture.json', 'index.html', 'style.css', 'app.js'];
const metrics = (passed, total, extra = {}) => ({
  pass_rate: passed / total, checks_passed: passed, checks_total: total, checks_failed: total - passed, ...extra,
});

test('passed QA uses qa.status, and skipped checks are named, never counted as passed', () => {
  const p = {
    status: 'completed',
    metrics: metrics(7, 8, { checks_failed: 0, checks_skipped: 1 }),
    qa: { status: 'passed', failed_checks: [], skipped_checks: ['QA-08'] },
  };
  const qa = qaSummary(p);
  assert.equal(qa.ok, true);
  assert.equal(qa.tone, 'done');
  assert.match(qa.text, /اجتاز 7 من 8/);
  assert.match(qa.text, /تخطّى 1/);
});

test('failed QA is not shown as success even when most checks passed', () => {
  const p = {
    status: 'completed',
    metrics: metrics(7, 8),
    qa: { status: 'failed', failed_checks: ['QA-05'], skipped_checks: [] },
  };
  const qa = qaSummary(p);
  assert.equal(qa.ok, false);
  assert.equal(qa.tone, 'failed');
  assert.match(qa.text, /فشل 1 من 8/);
  assert.ok(qa.note);
  assert.deepEqual(qa.failedChecks, ['QA-05']);
});

test('blocked and not_run QA say the quality is not verified', () => {
  const blocked = qaSummary({ status: 'failed', qa: { status: 'blocked' }, metrics: null });
  assert.equal(blocked.ok, false);
  assert.equal(blocked.text, 'تعذّر الاختبار');
  assert.match(blocked.note, /غير مؤكدة/);

  const notRun = qaSummary({ status: 'completed', qa: { status: 'not_run' }, metrics: null });
  assert.equal(notRun.ok, false);
  assert.equal(notRun.text, 'لم يُختبر');
});

test('equal numbers do not override a failed qa.status', () => {
  // A report can pass every check that ran while QA still failed (for example a check never ran).
  const qa = qaSummary({ status: 'completed', metrics: metrics(8, 8), qa: { status: 'failed', failed_checks: [] } });
  assert.equal(qa.ok, false);
});

test('a repair is counted only when the backend reports one', () => {
  assert.equal(repairCount({ repair_attempt: 0 }), 0);
  assert.equal(repairCount({}), 0);
  assert.equal(repairCount({ repair_attempt: null }), 0);
  assert.equal(repairCount({ repair_attempt: 1 }), 1);
});

test('the failed-checks message does not claim a repair', () => {
  assert.doesNotMatch(MSG.checksFailed(1, 8), /أصلح|لإصلاحه|للمطوّر/);
});

test('project list text follows qa.status', () => {
  const app = files(...APP, 'test_report.json');
  assert.match(projectStage({ status: 'completed', artifacts: app, metrics: metrics(8, 8), qa: { status: 'passed' } }), /اجتاز 8 من 8/);
  assert.match(projectStage({ status: 'completed', artifacts: app, metrics: metrics(6, 8), qa: { status: 'failed' } }), /فشل 2 من 8/);
  assert.equal(projectStage({ status: 'completed', artifacts: app, metrics: null, qa: { status: 'not_run' } }), 'مكتمل · لم يُختبر');
});

test('a failed run that produced the app is marked as usable in the list', () => {
  const p = { status: 'failed', artifacts: files(...APP), qa: { status: 'blocked' }, metrics: null };
  assert.equal(hasGeneratedApp(p), true);
  assert.equal(projectStage(p), 'توقف · التطبيق متاح');
});

test('repair history: only the steps the backend recorded, and no repair claimed without a change', async () => {
  const { repairSteps } = await import('../src/lib/qa.js');
  assert.equal(repairSteps({ repair: null }), null);
  const fixed = repairSteps({ repair: { max_repairs: 2, stopped: 'passed', history: [
    { attempt: 0, step: 'test', qa: { status: 'failed', passed: 7, total: 8, failed: [{ check_id: 'persist_after_refresh' }] } },
    { attempt: 1, step: 'repair', result: 'changed', changed_files: [{ file: 'app.js' }] },
    { attempt: 1, step: 'test', qa: { status: 'passed', passed: 8, total: 8, failed: [] } },
  ] } });
  assert.deepEqual(fixed.rows.map((r) => r.result), ['فشل 1 من 8', 'غيّر المطوّر: app.js', 'نجح 8 من 8']);
  const none = repairSteps({ repair: { stopped: 'no_change', history: [
    { attempt: 0, step: 'test', qa: { status: 'failed', passed: 7, total: 8, failed: [{}] } },
    { attempt: 1, step: 'repair', result: 'no_change', changed_files: [] },
  ] } });
  assert.equal(none.rows.length, 2);
  assert.equal(none.rows[1].result, 'لم يتغير أي ملف');
  assert.match(none.stopped, /لم يُحسب إصلاحاً/);
});

test('repair history marks AI repairs and rejected proposals', async () => {
  const { repairSteps } = await import('../src/lib/qa.js');
  const r = repairSteps({ repair: { stopped: 'invalid_repair_output', history: [
    { attempt: 0, step: 'test', qa: { status: 'failed', passed: 7, total: 8, failed: [{}] } },
    { attempt: 1, step: 'repair', result: 'changed', strategy: 'llm_repair', changed_files: [{ file: 'app.js' }] },
    { attempt: 1, step: 'test', qa: { status: 'failed', passed: 7, total: 8, failed: [{}] } },
    { attempt: 2, step: 'repair', result: 'rejected', reason: 'outside the allowlist' },
  ] } });
  assert.equal(r.rows[1].result, 'غيّر المطوّر (ذكاء اصطناعي): app.js');
  assert.equal(r.rows[3].result, 'رُفض اقتراح الإصلاح ولم يُطبَّق');
});
