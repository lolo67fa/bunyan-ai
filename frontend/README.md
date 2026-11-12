# Frontend

React user interface for BUNYAN AI.

**Owners:** Jood (React development, project dashboard) · Naifah (UI/UX design, assigned screens)

## Run

```bash
cd frontend
npm install
cp .env.example .env.local   # VITE_API_MODE=mock by default
npm run dev                  # http://localhost:5173
```

`npm run build` writes a static build to `dist/`.

## Screens

| Screen | Shown when `status` is | Component |
|---|---|---|
| Idea input | — (home, `#/`) | `pages/IdeaPage.jsx` |
| Agent progress dashboard | always on `#/projects/{id}` | `components/AgentTimeline.jsx` |
| Clarification questions | `awaiting_clarification` | `components/ClarificationForm.jsx` |
| Requirements review & approval | `awaiting_approval` | `components/RequirementsReview.jsx` |
| Approved, waiting for the Architect | `approved` | `pages/ProjectPage.jsx` |
| Out-of-scope / failure | `rejected` / `failed` | `pages/ProjectPage.jsx` + `components/OutOfScopeList.jsx` |
| Results: metrics, preview, ZIP | `completed` | `components/ResultsPanel.jsx` |
| Artifact view / download | any artifact available | `components/ArtifactList.jsx` |

The page polls `GET /projects/{id}` every `VITE_POLL_MS` ms and stops while the run waits for the user or has finished.

## Mock mode

`VITE_API_MODE=mock` runs a fake backend in the browser (`src/api/mockServer.js`) with the **same function names and response shape** as the real client (`src/api/httpClient.js`). Switching to the real backend is one line in `.env.local`: `VITE_API_MODE=http`.

- `requirements.json` uses the **real Business Analyst samples** from PR #2 (`backend/agents/business_analyst/samples/outputs/`), copied into `src/mocks/requirements/`. After the analyst contract changes, run `npm run sync-samples`.
- The idea text picks the sample (exact sample idea first, then keywords). The "sample ideas" buttons on the home page fill in the analyst's sample inputs.
  - vague idea → clarification questions → answers → task-manager requirements (same as `samples/answers/vague_idea_answers.json`)
  - payments / mobile app / chat → rejected as out of scope
  - Gulf-dialect inventory → shows one QA failure and one repair attempt
- `test_report.json` follows Sara's contract from PR #7. `architecture.json`, the generated app, `project_plan.md` and `risks.md` are **placeholders** (`src/mocks/placeholders.js`, marked `_mock`) until their owners share real samples.
- Mock runs are stored in `localStorage` (`bunyan.mock.projects.v2`), so a refresh keeps them.

## API contract

Based on Alanoud's backend in PR #5. Each line says whether PR #5 already has it.

```text
POST /projects                    body: { "prompt": "..." }                    → 201 Project       [PR #5]
GET  /projects/{project_id}                                                    → Project           [PR #5]
POST /projects/{project_id}/approve
                                  body: { "approved": true }                   → Project           [PR #5, returns 3 fields only]
                                     or { "approved": false, "feedback": "..." } → Project         [proposed]
POST /projects/{project_id}/answers
                                  body: { "answers": { "Q-1": "...", ... } }   → Project           [proposed]
GET  /projects/{project_id}/artifacts/{name}                                   → file content      [later]
GET  /projects/{project_id}/preview                                            → generated app     [later]
GET  /projects/{project_id}/download                                           → bunyan-output.zip [later]
```

`Project`:

```json
{
  "project_id": "uuid",
  "idea": "…",
  "status": "analyzing | awaiting_clarification | awaiting_approval | approved | rejected | designing | developing | testing | repairing | documenting | completed | failed",
  "current_agent": "business_analyst | software_architect | developer | qa_tester | project_manager | null",
  "requirements": "full requirements.json | null",
  "repair_attempt": 0,
  "artifacts": [{ "name": "requirements.json", "available": true }],
  "metrics": { "pass_rate": 1.0, "checks_passed": 8, "checks_total": 8, "run_time_seconds": 42 },
  "error": { "code": "...", "message": "…" },
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

- `project_id`, `idea`, `status`, `current_agent`, `requirements`: in PR #5.
- The rest are proposed. Until the backend sends them, `httpClient.js` fills safe defaults (`artifacts: []`, `repair_attempt: 0`, `metrics: null`, `error: null`), so the screens work with PR #5 as it is.
- `rejected`: out-of-scope idea (`requirements.status == "rejected_out_of_scope"`). The run stops and the screen lists `requirements.out_of_scope`.
- `approved`: requirements approved, next agent not started yet. The page keeps polling.
- If an action endpoint returns less than a full `Project` (approve in PR #5), the client re-reads `GET /projects/{project_id}`.

### QA report → `metrics`

The screens do not read `test_report.json` fields directly. The backend builds `Project.metrics` from Sara's report (PR #7, `tests/e2e/contract/TEST_REPORT.md` §4):

```text
metrics.pass_rate        ← test_report.summary.pass_rate     (number 0..1)
metrics.checks_passed    ← test_report.summary.passed
metrics.checks_total     ← test_report.summary.total         (always 8)
repair_attempt           ← test_report.run.attempt           (0 = first run, 1–2 after repair)
metrics.run_time_seconds ← orchestrator: whole pipeline, approve → completed
```

`run_time_seconds` is the whole pipeline (target ≤ 90 s), not `run.duration_ms`, which is the QA run only. The mock `test_report.json` uses Sara's exact shape (8 check ids, descriptions, `status`, `summary`, `run`, `defects`) and passes her Pydantic model `QAReport`.

Errors: FastAPI default `{ "detail": "..." }` (string or validation list). Proposed: a too-short or blank idea returns `422`, not `500`, so the screen can show the message.

## Open questions

| # | Question | With |
|---|---|---|
| F1 | Approve returns the full `Project`; approve accepts `{ approved: false, feedback }`; `POST /answers`; the proposed fields; `422` for invalid ideas | Alanoud |
| F4 | Preview origin: the generated app uses `localStorage`, so the iframe needs `allow-same-origin`; it must be served from a different origin than the frontend | Alanoud |
| F6 | `architecture.json` sample | Naifah |
| F7 | Confirm the QA → `metrics` mapping above, and that the orchestrator computes `run_time_seconds` | Sara, Alanoud |
| F8 | Generated file names (`index.html`, `style.css`, `app.js`) and a sample app for the preview | Yara |
| F9 | Bunyan visual identity: colours, fonts, wireframes (current styles are temporary) | Naifah |

The frontend must never contain LLM API keys; all model calls go through the backend.

## Running against the real backend

Verified on 2026-11-12 with the FastAPI backend on this branch (pipeline, QA, artifacts, preview, download).

1. Start the backend from the repository root. `npx` must be on its `PATH` for the QA stage (see `backend/orchestrator/README.md`):

   ```bash
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```

2. Create `frontend/.env.local` (git-ignored):

   ```
   VITE_API_MODE=http
   VITE_API_BASE_URL=http://127.0.0.1:8000
   ```

3. Start the frontend:

   ```bash
   npm ci
   npm run dev
   ```

The backend accepts browser requests only from a frontend on `localhost` or `127.0.0.1` (any port). For any other origin set `BUNYAN_CORS_ORIGINS` on the backend to a comma-separated list.

What the screens now take from the backend:

- `project.qa.status` decides whether the result is shown as passed. `passed` with skipped checks is still a pass; `failed`, `blocked` and `not_run` each show a note.
- An agent is shown as done only if it ran. With no Project Manager agent yet, it stays "لم يبدأ" on a completed run.
- Preview and download are offered whenever the three app files exist, including when QA could not run.
- Polling stops when a run is over, waits for the user, or the project does not exist. It keeps retrying while the server is unreachable.

## Tests

```bash
npm test        # logic in src/constants/stages.js, Node's built-in test runner
npm run build   # production build
```
