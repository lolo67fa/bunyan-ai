# Orchestrator

Runs the agents in order for one approved project.

**Owners:** Ghala (pipeline and its API integration), Alanoud (backend API)

## Status

Implemented and tested:

- **Pipeline** — approved requirements → Software Architect → Developer → stored application files.
- **API trigger** — `POST /projects/{id}/approve` starts the pipeline as a background task.
- **Results** — artifact, preview and download endpoints serve the generated files.

Not implemented yet:

- QA Tester step (Playwright) and the QA metrics shown by the frontend.
- QA ↔ Developer repair loop. `backend/agents/developer/repair.py` only coordinates attempts; no repair strategy exists.
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
| `completed` | `null` | all five files exist |
| `failed` | the agent that stopped | see `error` |

`completed` is set only after the five files are confirmed on disk and `app.js` has no unfilled template placeholder.

### Errors

A failed run ends with `status: "failed"` and `error: {"code", "message"}`. The function does not raise for these.

| `error.code` | Cause |
|---|---|
| `invalid_requirements` | requirements missing, malformed or not `ready_for_review` |
| `architecture_unsupported` | the Architect refused them (for example more than one entity) |
| `architecture_failed` | the Architect crashed on malformed input |
| `generation_failed` | the Developer refused or produced incomplete files |
| `storage_failed` | a file could not be written |
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

## Tests

```bash
python -m pytest tests/test_pipeline.py tests/test_storage.py tests/test_api_pipeline.py tests/test_artifacts_api.py
```

All of them run offline: no LLM, no network, no Node.js.

## Known limits

- Background tasks run inside the server process. A run does not survive a restart; it is marked `failed` at the next startup.
- All previews share the backend's origin, so two generated apps with the same entity name share one `localStorage` key in the same browser.

See [`../../docs/architecture.md`](../../docs/architecture.md) for the planned full workflow.
