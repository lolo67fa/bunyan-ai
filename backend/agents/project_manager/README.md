# Project Manager Agent

**Role owner:** Jood. This first version was written during the integration work (Ghala) because no implementation existed yet; it follows the draft format in `frontend/src/mocks/placeholders.js` (`mockProjectPlan`, `mockRisks`). Jood can replace or extend it behind the same function.

Writes two documents for one generated application:

- `project_plan.md` — summary, stages, deliverables, scope, recorded times.
- `risks.md` — open defects and risks.

It is deterministic: no LLM, no network, no API key.

## Use

```python
from backend.agents.project_manager import write_documents

write_documents(requirements, architecture, output_dir, qa_report=report, run=project, files=sizes)
```

| Argument | Content |
|---|---|
| `requirements` | approved `requirements.json` (dict) |
| `architecture` | `architecture.json` (dict) |
| `output_dir` | folder to write the two files into |
| `qa_report` | `test_report.json` (dict), or `None` when QA did not run |
| `run` | project state: `metrics`, `qa`, `repair_attempt`, `created_at` |
| `files` | generated file name → size in bytes |

`build_documents(...)` returns the two texts without writing them. Both raise `ProjectManagerError` when the requirements have no application name or the architecture has no entity.

The documents are written in the language of the requirements (`en` or `ar`).

## What it reports, and what it does not

Every line comes from the inputs:

- Counts and texts from the requirements (fields, functional requirements, stories, criteria, assumptions, out-of-scope items, questions answered with a default).
- The QA result from the report: passed, failed and skipped checks, each failed check's own error message and screenshot path, QA warnings word for word.
- Storage key, deferred rules and warnings from the architecture.
- File sizes and timestamps that were really recorded.

It does not estimate. Schedule, effort, cost and team assignment are not recorded by BUNYAN for a generated app, so the plan lists them under "Not available". When QA did not run or was blocked, the documents say the application was not tested; they never state a pass.

## Tests

```bash
python -m pytest backend/agents/project_manager/tests
```
