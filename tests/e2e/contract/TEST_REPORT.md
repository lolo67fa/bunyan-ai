# `test_report.json` contract — v0.1.0-proposal (NOT YET APPROVED)

**Owner:** Sara (QA Tester Agent)
**Inputs:** `requirements.json` `0.1.0-proposal` (Ghala) and the generated app (Yara), built on the `data-testid` rules of `architecture.json` `0.2.0-proposal` §5 (Naifah)
**Consumers:** Yara (Developer: repair loop), Jood (dashboard and PM agent), Alanoud (orchestrator, Pydantic model)
**Source of truth:** [`../lib/report.js`](../lib/report.js)

## 1. Principles

1. **Real runs only.** Every status and number comes from an actual Playwright run. A check that did not run is `not_run`, never `passed`.
2. **Fixed suite.** Always the same 8 check ids ([`../lib/checks.js`](../lib/checks.js)), in the same order.
3. **Input problems are not app defects.** If `requirements.json` cannot be tested (for example two entities), all checks are `not_run`, `run.blocked_reason` explains why, and `defects` is empty.

## 2. Shape

```text
schema_version   "0.1.0-proposal"
generated_at     ISO time
app              { name, language }                 from requirements.json
entity           entity name
inputs           { requirements_path, requirements_schema_version, app_dir, is_harness_fixture }
run              { attempt (0 = first run, 1–2 = re-test after repair), max_repair_attempts: 2,
                   started_at, finished_at, duration_ms, browser, playwright_version,
                   runner_status, blocked_reason }
summary          { total: 8, passed, failed, skipped, not_run, pass_rate (0..1), all_passed }
checks[8]        { id, description, status: passed | failed | skipped | not_run, duration_ms,
                   related_criteria [AC ids], error { message } | null, skip_reason,
                   evidence { screenshot, trace } }
defects[]        { check_id, message, evidence }    failed checks only — what goes to the Developer
warnings[]       string
```

- `pass_rate` = `passed / total`. Skipped and not-run checks count as not passed, so the 8/8 threshold means all 8 really passed.
- `related_criteria` matches `acceptance_criteria[].category` only. It shows which criteria a check relates to, not that each one is fully covered.
- Evidence paths are relative to the repository root.

## 3. Example (shortened, a real run on the fixture with a simulated storage defect)

```json
{
  "schema_version": "0.1.0-proposal",
  "app": { "name": "Task Manager", "language": "en" },
  "entity": "Task",
  "inputs": { "is_harness_fixture": true },
  "run": { "attempt": 1, "max_repair_attempts": 2, "duration_ms": 10632, "blocked_reason": null },
  "summary": { "total": 8, "passed": 7, "failed": 1, "skipped": 0, "not_run": 0, "pass_rate": 0.875, "all_passed": false },
  "checks": [
    { "id": "persist_after_refresh", "status": "failed", "related_criteria": ["AC-6"],
      "error": { "message": "record should survive a reload … Expected: 1 Received: 0" },
      "evidence": { "screenshot": "tests/e2e/reports/artifacts/…/test-failed-1.png", "trace": "…/trace.zip" } }
  ],
  "defects": [{ "check_id": "persist_after_refresh", "message": "…" }]
}
```

## 4. Mapping to what already exists

| Existing | Where | Proposal |
|---|---|---|
| `success_rate: str` | `backend/schemas/contracts.py` (`TestReportModel`) | Replace with `summary.pass_rate`, a number from 0 to 1 |
| `passed`, `failed` | `contracts.py` | Keep, under `summary` |
| `pass_rate`, `passed`, `total`, `checks[{id, passed}]` | `frontend/src/mocks/placeholders.js` | Same ids. `checks[].passed` (boolean) becomes `checks[].status` |
| `metrics.checks_passed / checks_total / run_time_seconds` | `frontend/src/components/ResultsPanel.jsx` | From `summary.passed`, `summary.total` and `run.duration_ms`. Note: `duration_ms` is the QA run only, not the whole pipeline |
| `repair_attempt` | frontend project state | Same value as `run.attempt` |

Nothing in other members' files is changed by this proposal. Each owner decides about their own files.

## 5. Open points

| # | Question | Who |
|---|---|---|
| T1 | Approve the 8 check ids (same as Jood's mock)? | Jood, team |
| T2 | `pass_rate` number (0..1) instead of `success_rate` string? | Alanoud, Jood |
| T3 | Are `defects[].message` and evidence enough for the repair loop, or does the Developer need expected/actual as separate fields? | Yara |
| T4 | Confirm the `data-testid` names in architecture §5 (answer to A2: the 8 checks do not need `search-input` or `filter-*`) | Naifah, Yara |
| T5 | AC-2 in `task_manager_en` expects errors for Priority and Status, but both have defaults and cannot be empty | Ghala |
| T6 | Single entity in v0.1 (D9): the suite refuses documents with several entities | Ghala, Naifah, Yara |
| T7 | How the orchestrator runs the suite (Node subprocess with `REQUIREMENTS`, `APP_DIR` and `QA_ATTEMPT`) and where it stores the report | Alanoud |
