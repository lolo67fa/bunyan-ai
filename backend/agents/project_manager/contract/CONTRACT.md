# Project Manager Agent: contract (0.1.0-proposal)

For the orchestrator (Alanoud) and the frontend. Pydantic models in `schema.py` are the source of truth; `python -m backend.agents.project_manager --schema` prints them as JSON Schema.

## When it runs

After the QA Tester's last run, while the workflow status is `documenting`. It may also run on a stopped run (`failed`) to produce a partial plan.

## Input: `PMInput`

| Field | Type | Notes |
|---|---|---|
| `requirements` | object | **Required.** `requirements.json`. Must have `app` and `entities`. |
| `architecture` | object \| null | `architecture.json` (reads `entity.storage`, `screens`, `warnings`, `deferred_rules`). |
| `test_report` | object \| null | Latest `test_report.json` (reads `summary`, `checks[].status/error`, `run.attempt/blocked_reason`). |
| `status` | string | Workflow status. Default `documenting`. |
| `generated_files` | string[] | E.g. `["index.html", "style.css", "app.js"]`. |
| `repair_attempt` | int 0–2 | Repairs used. `test_report.run.attempt` wins when higher. |
| `run_time_seconds` | number \| null | Approval to now, whole pipeline. Compared with the 90 s target. |
| `stage_seconds` | object | Optional: `requirements`, `structure`, `development`, `tests`, `documentation`. |
| `language` | `ar` \| `en` \| null | Defaults to `requirements.language`. |

Unknown fields are ignored, so the other agents' contracts can grow without breaking this one.

## Output: `PMResult`

| Field | Notes |
|---|---|
| `project_plan_md`, `risks_md` | The two documents. `write_outputs()` saves them as `project_plan.md` and `risks.md`. |
| `status` | `complete` when every stage is done, else `partial`. |
| `summary` | One to three sentences (rule-based, or written by the model in LLM mode). |
| `stages[]` | `key`, `owner`, `output`, `status` (`done` · `in_progress` · `failed` · `not_started`), `seconds`. |
| `risks[]` | `id` (`R-1`…; LLM extras `R-L1`…), `title`, `likelihood`, `impact` (`low` · `medium` · `high`), `mitigation`, `status` (`open` · `closed`), `source`. |
| `mode`, `language`, `warnings`, `schema_version` | `warnings` explains a skipped LLM step. |

## Suggested API use

- Save both files as project artifacts so `GET /projects/{id}/artifacts/project_plan.md` and `.../risks.md` serve them (the frontend's Plan tab already reads these names).
- Optionally return `summary` and the open-risk count in the project response.

## Open points

1. Who measures `stage_seconds` and `run_time_seconds`: the orchestrator (proposed).
2. Should the PM step run again after a manual re-run of a failed stage? (Proposed: yes, it is cheap in rules mode.)
