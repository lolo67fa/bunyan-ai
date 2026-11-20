# QA Tester Agent

**Owner:** Sara

Runs the fixed Playwright suite in [`tests/e2e`](../../../tests/e2e) on one generated app, checks `test_report.json` with Pydantic, and adds the run to a quality log. It has no LLM: results come only from the real browser run.

## Use

```python
from backend.agents.qa_tester import run_qa

report = run_qa(
    app_dir="path/to/generated/app",          # folder with index.html
    requirements_path="path/to/requirements.json",
    attempt=0,                                # 0 = first run, 1-2 = re-test after a repair
    architecture_path="path/to/architecture.json",  # optional: verbatim texts and number formats
)
report["summary"]["all_passed"]   # True only if all 8 checks passed
report["defects"]                 # failed checks, to send to the Developer
```

Needs Node.js and, once, `npm install` and `npx playwright install chromium` in `tests/e2e`.

## What it does

1. Checks the inputs: `index.html` exists, `requirements.json` exists, `architecture.json` exists when given, `attempt` is 0, 1 or 2 (at most 2 repair attempts).
2. Deletes the previous report, so old results are never returned.
3. Runs `npx playwright test` in `tests/e2e`, passing `APP_DIR`, `REQUIREMENTS`, `ARCHITECTURE` and `QA_ATTEMPT`.
4. Reads `tests/e2e/reports/test_report.json` and validates it with `QAReport` (`schema.py`). The summary must match the checks: no invented passes.
5. Adds one line to `tests/e2e/reports/quality_log.csv`: time, app, attempt, passed/total, pass rate, run time, failed checks.

A failed check is **not** an error: the report is returned with `failed` checks and `defects`. Errors are raised only for bad inputs or when Playwright could not produce a report.

## Files

| File | Purpose |
|---|---|
| `runner.py` | `run_qa()`, the entry point for the orchestrator |
| `schema.py` | Pydantic model of `test_report.json` (format `0.1.0-proposal`, see `tests/e2e/contract/TEST_REPORT.md`) |
| `quality_log.py` | Adds one CSV line per run |
| `tests/test_qa_tester.py` | Unit tests plus two real runs on the harness fixture |

## Tests

From the repository root:

```bash
python -m pytest backend/agents/qa_tester/tests -v
```

The real-run tests are skipped when Node.js is not installed. The Appointment run (required select without a default) is skipped until the Architect samples are on the branch (PR #4).

## Open points

- How the orchestrator calls `run_qa()` and where it stores the report (Alanoud).
- The report format is a proposal until the team agrees (see `tests/e2e/contract/TEST_REPORT.md` §5).