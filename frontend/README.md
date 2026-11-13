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

Built to the approved design (direction C, calm green). Tokens: `src/styles/tokens.css`; brand files: `brand/`.

| Route | Screen | File |
|---|---|---|
| `#/` | Landing page | `pages/LandingPage.jsx` |
| `#/new` | New project (idea, examples, what Bunyan can build) | `pages/NewProjectPage.jsx` |
| `#/projects` | Projects: filters, search, "waiting for you" notice | `pages/ProjectsPage.jsx` |
| `#/projects/<id>` | Changes with the run status (below) | `pages/ProjectPage.jsx` |
| `#/projects/<id>/<tab>` | `requirements`, `structure`, `files`, `tests`, `plan`, `preview` | `project/*View.jsx` |
| `#/settings`, `#/help` | Appearance, reduced motion, FAQ | `pages/SettingsPage.jsx` |

Project page by status:

| Status | What the user sees |
|---|---|
| `analyzing` | Agent steps, analyst working |
| `awaiting_clarification` | Clarification questions (`ClarificationView`) |
| `awaiting_approval` | Requirements review with approve and request-changes dialog |
| `approved` … `documenting` | Build progress (`ProgressView`); finished stages open as tabs |
| `completed` | Delivery page (`DeliveryView`), all tabs available |
| `rejected`, `failed` | What happened and what to do next (`StoppedView`) |

Waiting and errors follow the approved table: polling every 3 s, stopped after 3 failed requests in a row with a retry button; requests time out after 15 s; a long-running agent shows a note after 30 s and options after 5 minutes. Messages live in `src/lib/messages.js`.

The projects list is kept in this browser (`localStorage`), because the API has no list endpoint yet (proposed: `GET /projects`).

## Mock mode

`VITE_API_MODE=mock` runs a fake backend in the browser (`src/api/mockServer.js`) with the **same function names and response shape** as the real client (`src/api/httpClient.js`). Switching to the real backend is one line in `.env.local`: `VITE_API_MODE=http`.

- `requirements.json` uses the **real Business Analyst samples** from PR #2 (`backend/agents/business_analyst/samples/outputs/`), copied into `src/mocks/requirements/`. After the analyst contract changes, run `npm run sync-samples`.
- The idea text picks the sample (exact sample idea first, then keywords). The "sample ideas" buttons on the home page fill in the analyst's sample inputs.
  - vague idea → clarification questions → answers → task-manager requirements (same as `samples/answers/vague_idea_answers.json`)
  - payments / mobile app / chat → rejected as out of scope
  - Gulf-dialect inventory → shows one QA failure and one repair attempt
- `test_report.json` follows Sara's contract from PR #7, and `architecture.json` uses Naifah's real samples from PR #4 where one exists. The generated app, `project_plan.md` and `risks.md` are **placeholders** (`src/mocks/placeholders.js`, marked `_mock`) until their owners share real samples.
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
