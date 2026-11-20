// What the review screens say after the Business Analyst runs: never that a change was
// applied unless the backend's revision lists it. Runs with `npm test`.

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { analysisNotices, revisionSummary } from '../src/lib/analysis.js';

const req = { status: 'ready_for_review', language: 'en', entities: [] };
const ids = (project) => analysisNotices(project).map((n) => n.testId);

test('an applied revision names what really changed', () => {
  const revision = {
    feedback: 'Add a phone number field', mode: 'llm', changed: true,
    added_fields: [{ entity: 'Task', field: 'phone', label: 'Phone number' }], removed_fields: [], changed_fields: [],
  };
  const [notice] = analysisNotices({ status: 'awaiting_approval', requirements: req, revision });
  assert.equal(notice.testId, 'revision-applied');
  assert.match(notice.text, /أضاف: Phone number/);
  assert.match(notice.text, /Add a phone number field/);
});

test('an unchanged revision is never shown as applied', () => {
  const llm = { feedback: 'Add a phone field', mode: 'llm', changed: false, added_fields: [] };
  const mock = { ...llm, mode: 'mock' };
  for (const revision of [llm, mock]) {
    const notices = analysisNotices({ status: 'awaiting_approval', requirements: req, revision });
    assert.deepEqual(notices.map((n) => n.testId), ['revision-unchanged']);
    assert.doesNotMatch(notices[0].text, /ما تغيّر/);
  }
  assert.match(analysisNotices({ status: 'awaiting_approval', requirements: req, revision: mock })[0].text, /الوضع التجريبي/);
  assert.equal(revisionSummary(llm), null);
});

test('a failed re-analysis shows its safe message and that the last version is kept', () => {
  const error = { code: 'llm_rate_limited', message: 'خدمة الذكاء الاصطناعي مزدحمة الآن.', retryable: true };
  const [notice] = analysisNotices({ status: 'awaiting_approval', requirements: req, error });
  assert.equal(notice.tone, 'error');
  assert.match(notice.text, /مزدحمة/);
  assert.match(notice.text, /آخر نسخة/);
});

test('the Architect warning appears before approval only', () => {
  const compatibility = { supported: false, message: 'نوع سجل واحد', reasons: ['MVP supports exactly one entity'] };
  assert.deepEqual(ids({ status: 'awaiting_approval', requirements: req, compatibility }), ['compatibility-warning']);
  assert.deepEqual(ids({ status: 'designing', requirements: req, compatibility }), []);
  assert.deepEqual(ids({ status: 'awaiting_approval', requirements: req, compatibility: { supported: true } }), []);
});

test('nothing is shown while analysing or without a project', () => {
  assert.deepEqual(ids({ status: 'analyzing', revision: { changed: false, feedback: 'x' } }), []);
  assert.deepEqual(analysisNotices(null), []);
});
