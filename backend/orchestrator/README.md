# Orchestrator

Runs the agents in order for one approved project.

**Owners:** Ghala (pipeline and its API integration), Alanoud (backend API)

## Status

Implemented and tested:

- **Pipeline** — approved requirements → Software Architect → Developer → QA Tester → stored files.
- **QA** — Sara's QA Tester (`run_qa`, Playwright, 8 checks) runs once on every generated app. Its real report is stored and its numbers become `project["metrics"]`.
- **API trigger** — `POST /projects/{id}/approve` starts the pipeline as a background task.
- **Results** — artifact, preview and download endpoints serve the generated files and the QA report.

Not implemented yet:

- QA ↔ Developer repair loop. `backend/agents/developer/repair.py` only coordinates attempts; no repair strategy exists, so QA runs once (`attempt` 0) and `repair_attempt` stays 0.
- Project Manager agent (`project_plan.md`, `risks.md`).
- CrewAI. The Architect and Developer are deterministic Python functions, so the pipeline calls them directly.

The Business Analyst runs before this pipeline, in `POST /projects`, and is still fixed to mock mode in `backend/main.py`.

## Pipeline

```python
from backend.orchestrator import run_pipeline

project = run_pipeline(project, workdir, on_update)
```

`run_pipeline(project: dict, workdir: Path, on_update: Callable[[dict], None]) -> dict`

- `project` — the project state dict. It must have `requirements_approved: True` and a `requirements` document with status `ready_for_review`. It is updated in place and returned; other fields are kept.
- `workdir` — the folder to write into.
- `on_update` — called with the project after every state change, so the caller can save it.

The module does not import FastAPI or `backend/storage.py`.

### States

| Status | `current_agent` | Meaning |
|---|---|---|
| `designing` | `software_architect` | `build_architecture()` is running |
| `developing` | `developer` | `generate()` is running |
| `testing` | `qa_tester` | `run_qa()` is running |
| `completed` | `null` | the app exists and QA gave a result |
| `failed` | the agent that stopped | see `error` |

The Developer's five files are confirmed on disk, and `app.js` checked for an unfilled template placeholder, before QA starts.

### QA result

`project["qa"]["status"]` says how testing ended. `completed` alone does not mean the app passed.

| `status` | `qa.status` | Meaning |
|---|---|---|
| `completed` | `passed` | no check failed, and every check either passed or was skipped with a reason |
| `completed` | `failed` | the app was generated and QA found real defects; see `test_report.json` |
| `completed` | `not_run` | QA is switched off (`BUNYAN_QA=off`); `metrics` stays `null` |
| `failed` | `blocked` | QA could not test the app or crashed; `error.code` is `qa_blocked` or `qa_failed` |

Skipped checks are counted on their own and never as passed. A report whose summary disagrees with its checks is rejected. The generated app stays available for preview and download in every case.

`project["metrics"]` comes from the report:

| Field | Source |
|---|---|
| `pass_rate` | `summary.pass_rate` |
| `checks_passed` / `checks_total` | `summary.passed` / `summary.total` |
| `checks_failed` / `checks_skipped` / `checks_not_run` | `summary.failed` / `summary.skipped` / `summary.not_run` |
| `run_time_seconds` | whole pipeline, measured by the orchestrator |

The stored `test_report.json` is the report Playwright wrote, with two changes: paths in `inputs` and in `evidence` point inside the project folder, and server paths are removed. Screenshots and traces of failed checks are copied to `qa_evidence/`.

### Errors

A failed run ends with `status: "failed"` and `error: {"code", "message"}`. The function does not raise for these.

| `error.code` | Cause |
|---|---|
| `invalid_requirements` | requirements missing, malformed or not `ready_for_review` |
| `architecture_unsupported` | the Architect refused them (for example more than one entity) |
| `architecture_failed` | the Architect crashed on malformed input |
| `generation_failed` | the Developer refused or produced incomplete files |
| `storage_failed` | a file could not be written |
| `qa_blocked` | the QA suite cannot test this app, or some checks never ran |
| `qa_failed` | QA could not run (Node.js missing, timeout, no report, invalid report) |
| `pipeline_failed` | unexpected error, set by `backend/main.py` |
| `pipeline_interrupted` | the server restarted during a run, set at startup by `backend/main.py` |

`run_pipeline` raises `PipelineNotApproved` if the project is not approved. That is a mistake in the caller, so the project is left unchanged.

## Files

Generated files are stored per project and are git-ignored:

```
backend/data/{project_id}.json           project state
backend/data/{project_id}/requirements.json
backend/data/{project_id}/architecture.json
backend/data/{project_id}/app/index.html
backend/data/{project_id}/app/style.css
backend/data/{project_id}/app/app.js
backend/data/{project_id}/test_report.json
backend/data/{project_id}/qa_evidence/   screenshots and traces of failed checks
```

`project["artifacts"]` lists only files that exist, as `{"name", "available", "path"}`.

## API

| Method | Path | Result |
|---|---|---|
| `POST` | `/projects/{id}/approve` | Sets `designing`, answers at once, runs the pipeline in the background. A second approval gets `409`. |
| `GET` | `/projects/{id}/artifacts/{name}` | One generated file. |
| `GET` | `/projects/{id}/preview/` | The generated app. `/preview` redirects here so the app's relative links to `style.css` and `app.js` resolve. |
| `GET` | `/projects/{id}/preview/{filename}` | `index.html`, `style.css` or `app.js`. |
| `GET` | `/projects/{id}/download` | ZIP of the generated files. `404` until all five exist. |

Artifact names are a fixed list in `backend/artifacts.py`: `requirements.json`, `architecture.json`, `index.html`, `style.css`, `app.js`, and — once the QA and Project Manager agents write them — `test_report.json`, `project_plan.md`, `risks.md`. Any other name gives `404`.

Preview responses carry a Content-Security-Policy that lets the generated app load only its own files. It cannot call this API or any other host.

## Running QA

QA needs Node.js 20 or newer, the suite's packages and Chromium:

```bash
cd tests/e2e
npm ci
npx playwright install chromium
```

`npx` must be on the `PATH` of the process that runs the backend. Without it a run ends `failed` with `error.code: "qa_failed"`. Set `BUNYAN_QA=off` to generate apps without testing them.

## Tests

```bash
python -m pytest tests/test_pipeline.py tests/test_storage.py tests/test_api_pipeline.py tests/test_artifacts_api.py tests/test_qa_pipeline.py
```

These run offline (no LLM, no network), with QA switched off by `tests/conftest.py`. The exception is five tests in `tests/test_qa_pipeline.py` that run the real QA suite on generated apps; they are skipped, with the reason shown, when Node.js or `tests/e2e/node_modules` is missing.

## Known limits

- One QA run at a time. The QA runner writes to one report file, serves on one port (4317) and shares one screenshot folder, so the orchestrator takes a lock around it: a thread lock inside the server process, plus a file lock for other processes on the same machine (not on Windows). Projects approved together are tested one after another, about 3 seconds each.
- QA evidence in `qa_evidence/` is stored but has no endpoint yet.
- Background tasks run inside the server process. A run does not survive a restart; it is marked `failed` at the next startup.
- All previews share the backend's origin, so two generated apps with the same entity name share one `localStorage` key in the same browser.

See [`../../docs/architecture.md`](../../docs/architecture.md) for the planned full workflow.
