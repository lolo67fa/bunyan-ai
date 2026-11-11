# `test_report.json` contract — v0.2.0-proposal

**Owner:** Sara (QA Tester Agent)
**Inputs:** `requirements.json` (Ghala) and the generated app (Yara). When given, `architecture.json` `0.3.0-proposal` (Naifah) for the verbatim texts, `empty_option` and `display_format`. Element names follow its `data-testid` rules (§5).
**Consumers:** Yara (Developer: repair loop), Jood (dashboard and PM agent), Alanoud (orchestrator, Pydantic model)
**Source of truth:** [`../lib/report.js`](../lib/report.js), validated by `QAReport` in `backend/agents/qa_tester/schema.py`

### Changes in v0.2.0

| Request | Change |
|---|---|
| Required dropdown without a default (Ghala, PR #8) | The two empty-input checks now leave such a select empty and expect its error. With `architecture.json`, a missing `empty_option` fails both checks. Required fields **with** a default are never left empty. |
| Rule M1 for messages (Ghala, Naifah PR #4) | Texts in `verbatim_messages` are compared **exactly**. All other messages are only checked to be **visible** (§3). |
| New testid `confirm-delete-text` (Naifah) | `delete_item` checks it shows the record name, and compares it exactly when it is verbatim. |
| `display_format` (Ghala, Naifah) | `list_items` checks number columns show exactly the given decimals (for example price `12.50`). |
| Traceability | New `checks[].verbatim_compared`, `inputs.architecture_path` and `inputs.architecture_schema_version`. |

All changes are additions: every v0.1.0 field keeps its name and meaning.

## 1. Principles

1. **Real runs only.** Every status and number comes from an actual Playwright run. A check that did not run is `not_run`, never `passed`.
2. **Fixed suite.** Always the same 8 check ids ([`../lib/checks.js`](../lib/checks.js)), in the same order.
3. **Input problems are not app defects.** If `requirements.json` or `architecture.json` cannot be tested (for example two entities, or files for different entities), all checks are `not_run`, `run.blocked_reason` explains why, and `defects` is empty.
4. **Say what was not checked.** Anything the 8 checks cannot verify is listed in `warnings`.

## 2. Shape

```text
schema_version   "0.2.0-proposal"
generated_at     ISO time
app              { name, language }                 from requirements.json
entity           entity name
inputs           { requirements_path, requirements_schema_version,
                   architecture_path, architecture_schema_version,   (null without architecture.json)
                   app_dir, is_harness_fixture }
run              { attempt (0 = first run, 1–2 = re-test after repair), max_repair_attempts: 2,
                   started_at, finished_at, duration_ms, browser, playwright_version,
                   runner_status, blocked_reason }
summary          { total: 8, passed, failed, skipped, not_run, pass_rate (0..1), all_passed }
checks[8]        { id, description, status: passed | failed | skipped | not_run, duration_ms,
                   related_criteria [AC ids], error { message } | null, skip_reason,
                   verbatim_compared [{ path, text, source }],
                   evidence { screenshot, trace } }
defects[]        { check_id, message, evidence }    failed checks only — what goes to the Developer
warnings[]       string
```

- `pass_rate` = `passed / total`. Skipped and not-run checks count as not passed, so the 8/8 threshold means all 8 really passed.
- `run.duration_ms` is the QA run only. The whole pipeline time is measured by the backend (Alanoud).
- `related_criteria` matches `acceptance_criteria[].category` only. It shows which criteria a check relates to, not that each one is fully covered.
- `verbatim_compared` lists the texts a check compared exactly and passed, with the acceptance criterion they came from.
- Evidence paths are relative to the repository root.

## 3. Messages (rule M1)

| Text | How it is checked | Check |
|---|---|---|
| `screens.form.save_button` in `verbatim_messages` | `btn-save` text equals it | `create_item` |
| `messages.delete_button`, `messages.confirm_button` | `btn-delete`, `btn-confirm-delete` text equals it | `delete_item` |
| `messages.confirm_delete` | `confirm-delete-text` equals it, with `{display}` replaced by the record name | `delete_item` |
| `messages.empty` | `empty-state` equals it | `empty_state` |
| `entity.fields.<f>.messages.required` | `error-<f>` equals it | `error_message_visible` |
| Any message **not** in `verbatim_messages` | Visible and not empty | same checks |
| `messages.no_results` and other field rules (min length, date, …) | **Not checked**: search and those rules are not in the 8 checks. Listed in `warnings`. | — |

Without `architecture.json`, messages are only checked to be visible, and `warnings` says so.

## 4. Example (shortened, a real run on the fixture with a simulated storage defect)

```json
{
  "schema_version": "0.2.0-proposal",
  "app": { "name": "Task Manager", "language": "en" },
  "entity": "Task",
  "inputs": { "architecture_path": "backend/agents/architect/samples/outputs/task_manager_en.architecture.json",
              "is_harness_fixture": true },
  "run": { "attempt": 1, "max_repair_attempts": 2, "duration_ms": 10632, "blocked_reason": null },
  "summary": { "total": 8, "passed": 7, "failed": 1, "skipped": 0, "not_run": 0, "pass_rate": 0.875, "all_passed": false },
  "checks": [
    { "id": "create_item", "status": "passed",
      "verbatim_compared": [{ "path": "screens.form.save_button", "text": "Save", "source": "AC-1" }] },
    { "id": "persist_after_refresh", "status": "failed", "related_criteria": ["AC-6"],
      "error": { "message": "record should survive a reload … Expected: 1 Received: 0" },
      "verbatim_compared": [],
      "evidence": { "screenshot": "tests/e2e/reports/artifacts/…/test-failed-1.png", "trace": "…/trace.zip" } }
  ],
  "defects": [{ "check_id": "persist_after_refresh", "message": "…" }]
}
```

## 5. Mapping to what already exists

| Existing | Where | Status |
|---|---|---|
| `success_rate: str` | `backend/schemas/contracts.py` (`TestReportModel`) | Agreed to replace with `summary.pass_rate`, a number from 0 to 1 (T2). Change is up to Alanoud. |
| `passed`, `failed` | `contracts.py` | Keep, under `summary` |
| Dashboard metrics and mock report | `frontend/` | Done by Jood in PR #9: same 8 ids and fields, validated with `QAReport` |
| `repair_attempt` | frontend project state | Same value as `run.attempt` |

Nothing in other members' files is changed by this contract. Each owner decides about their own files.

## 6. Open points

| # | Question | Who | Status |
|---|---|---|---|
| T1 | Approve the 8 check ids (same as Jood's mock)? | Jood | ✅ Agreed (Jood) |
| T2 | `pass_rate` number (0..1) instead of `success_rate` string? `run.duration_ms` is the QA run only? | Jood, Alanoud | ✅ Agreed (Jood). `contracts.py` still to update (Alanoud) |
| T3 | Are `defects[].message` and evidence enough for the repair loop, or does the Developer need expected/actual as separate fields? | Yara | Open |
| T4 | `data-testid` names in architecture §5 | Naifah, Yara | ✅ Used as in 0.3.0, including `confirm-delete-text`. Yara to confirm the template follows them |
| T5 | AC-2 expected errors for fields with defaults | Ghala | ✅ Fixed in PR #8. Required dropdowns without a default are now tested (§3) |
| T6 | Single entity in v0.1 (D9): the suite refuses documents with several entities | Ghala, Naifah, Yara | Open (same rule as the Architect) |
| T7 | How the orchestrator calls `run_qa()` and where it stores the report | Alanoud | Open |
| T8 | `no-results` and search are not in the 8 checks. Add a 9th check later, or keep them out of the MVP? | Team | Open |

### Answer to the Architect's open question A2 (Naifah)

Yes: `verbatim_messages` are compared exactly and everything else by visibility (§3). `confirm-delete-text` is checked in `delete_item`. `no-results` is not used yet, because search is not one of the 8 checks (T8).
