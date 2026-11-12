// Frontend logic that decides what the screens show for a project from the real backend.
// Runs with Node's built-in test runner: `npm test` (no extra packages).

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  AGENTS,
  STATUS_LABELS,
  agentState,
  hasGeneratedApp,
  qaOutcome,
  shouldStopPolling,
} from '../src/constants/stages.js';

const files = (...names) => names.map((name) => ({ name, available: true }));
const APP = ['requirements.json', 'architecture.json', 'index.html', 'style.css', 'app.js'];
const states = (project) => AGENTS.map((_, i) => agentState(i, project));

// Shapes copied from what backend/main.py returns at each stage.
const backend = {
  awaitingApproval: { status: 'awaiting_approval', current_agent: 'business_analyst', artifacts: [] },
  designing: { status: 'designing', current_agent: 'software_architect', artifacts: [] },
  developing: { status: 'developing', current_agent: 'developer', artifacts: files('requirements.json', 'architecture.json') },
  testing: { status: 'testing', current_agent: 'qa_tester', artifacts: files(...APP) },
  completed: {
    status: 'completed',
    current_agent: null,
    artifacts: files(...APP, 'test_report.json'),
    metrics: { pass_rate: 1, checks_passed: 8, checks_total: 8, run_time_seconds: 3.1 },
    qa: { status: 'passed', failed_checks: [], skipped_checks: [] },
  },
  qaBlocked: {
    status: 'failed',
    current_agent: 'qa_tester',
    artifacts: files(...APP),
    error: { code: 'qa_failed', message: 'QA could not run: npx not found. Install Node.js first.' },
    qa: { status: 'blocked' },
    metrics: null,
  },
  unsupported: {
    status: 'failed',
    current_agent: 'software_architect',
    artifacts: files('requirements.json'),
    error: { code: 'architecture_unsupported', message: 'MVP supports exactly one entity' },
  },
  rejected: { status: 'rejected', current_agent: 'business_analyst', artifacts: [] },
};

test('every backend status has an Arabic label', () => {
  for (const status of ['analyzing', 'awaiting_clarification', 'awaiting_approval', 'rejected', 'designing', 'developing', 'testing', 'completed', 'failed']) {
    assert.ok(STATUS_LABELS[status], status);
  }
  assert.equal(STATUS_LABELS.generating, undefined); // the backend must keep using "developing"
});

test('timeline follows the pipeline stages', () => {
  assert.deepEqual(states(backend.awaitingApproval), ['waiting', 'pending', 'pending', 'pending', 'pending']);
  assert.deepEqual(states(backend.designing), ['done', 'active', 'pending', 'pending', 'pending']);
  assert.deepEqual(states(backend.developing), ['done', 'done', 'active', 'pending', 'pending']);
  assert.deepEqual(states(backend.testing), ['done', 'done', 'done', 'active', 'pending']);
});

test('completed run does not show the Project Manager as done when it never ran', () => {
  assert.deepEqual(states(backend.completed), ['done', 'done', 'done', 'done', 'pending']);
});

test('Project Manager is done once its plan exists', () => {
  const withPlan = { ...backend.completed, artifacts: [...backend.completed.artifacts, ...files('project_plan.md', 'risks.md')] };
  assert.deepEqual(states(withPlan), ['done', 'done', 'done', 'done', 'done']);
});

test('QA is not shown as done when it was switched off', () => {
  const noQa = { status: 'completed', current_agent: null, artifacts: files(...APP), metrics: null, qa: { status: 'not_run' } };
  assert.deepEqual(states(noQa), ['done', 'done', 'done', 'pending', 'pending']);
});

test('failed and rejected runs mark the agent that stopped', () => {
  assert.deepEqual(states(backend.qaBlocked), ['done', 'done', 'done', 'failed', 'pending']);
  assert.deepEqual(states(backend.unsupported), ['done', 'failed', 'pending', 'pending', 'pending']);
  assert.deepEqual(states(backend.rejected), ['failed', 'pending', 'pending', 'pending', 'pending']);
});

test('polling continues while the pipeline works', () => {
  for (const project of [backend.designing, backend.developing, backend.testing, { status: 'analyzing' }]) {
    assert.equal(shouldStopPolling(project, null), false, project.status);
  }
});

test('polling stops when the run is over or waits for the user', () => {
  for (const project of [backend.completed, backend.qaBlocked, backend.unsupported, backend.rejected, backend.awaitingApproval, { status: 'awaiting_clarification' }]) {
    assert.equal(shouldStopPolling(project, null), true, project.status);
  }
});

test('polling stops for a project that does not exist, but retries when the server is unreachable', () => {
  assert.equal(shouldStopPolling(null, { status: 404 }), true);
  assert.equal(shouldStopPolling(null, { status: 422 }), true); // id is not a UUID
  assert.equal(shouldStopPolling(null, { status: 0 }), false); // backend down: keep trying
  assert.equal(shouldStopPolling(null, { status: 500 }), false);
  assert.equal(shouldStopPolling(null, null), false);
});

test('generated app is offered only when its three files exist', () => {
  assert.equal(hasGeneratedApp(backend.completed), true);
  assert.equal(hasGeneratedApp(backend.qaBlocked), true); // QA failed to run, the app is still there
  assert.equal(hasGeneratedApp(backend.unsupported), false);
  assert.equal(hasGeneratedApp(backend.developing), false);
  assert.equal(hasGeneratedApp({ artifacts: [{ name: 'app.js', available: false }] }), false);
  assert.equal(hasGeneratedApp({}), false);
});

test('QA outcome comes from the backend, not from comparing numbers', () => {
  assert.deepEqual(qaOutcome(backend.completed), { status: 'passed', ok: true, failedChecks: [], skippedChecks: [] });

  const skipped = {
    metrics: { checks_passed: 6, checks_total: 8 },
    qa: { status: 'passed', failed_checks: [], skipped_checks: ['reject_incomplete_input', 'error_message_visible'] },
  };
  assert.equal(qaOutcome(skipped).ok, true); // 6/8 with two skipped is still a pass
  assert.equal(qaOutcome(skipped).skippedChecks.length, 2);

  const defects = { metrics: { checks_passed: 7, checks_total: 8 }, qa: { status: 'failed', failed_checks: ['persist_after_refresh'] } };
  assert.equal(qaOutcome(defects).ok, false);
  assert.deepEqual(qaOutcome(defects).failedChecks, ['persist_after_refresh']);

  assert.equal(qaOutcome(backend.qaBlocked).ok, false);
  assert.equal(qaOutcome(backend.qaBlocked).status, 'blocked');
  assert.equal(qaOutcome({ qa: { status: 'not_run' }, metrics: null }).ok, false);
});

test('QA outcome without a qa field (mock mode) falls back to the numbers', () => {
  assert.equal(qaOutcome({ metrics: { checks_passed: 8, checks_total: 8 } }).ok, true);
  assert.equal(qaOutcome({ metrics: { checks_passed: 7, checks_total: 8 } }).status, 'failed');
  assert.equal(qaOutcome({ metrics: null }).status, 'unknown');
});
