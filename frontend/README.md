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
| Out-of-scope / failure | `failed` | `pages/ProjectPage.jsx` + `components/OutOfScopeList.jsx` |
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
- `architecture.json`, `test_report.json`, the generated app, `project_plan.md` and `risks.md` are **placeholders** (`src/mocks/placeholders.js`, marked `_mock`) until their owners share real samples.
- Mock runs are stored in `localStorage` (`bunyan.mock.projects`), so a refresh keeps them.

## Proposed API contract (needs agreement with Alanoud)

Endpoints follow `docs/architecture.md` §5. The payloads below are what `httpClient.js` sends and expects today.

```text
POST /projects                    body: { "idea": "..." }                      → Project
GET  /projects/{id}                                                            → Project
POST /projects/{id}/answers       body: { "answers": { "Q-1": "...", ... } }   → Project
POST /projects/{id}/approve       body: { "approved": true }
                                     or { "approved": false, "feedback": "..." } → Project
GET  /projects/{id}/artifacts/{name}                                           → file content
GET  /projects/{id}/preview                                                    → generated app (HTML)
GET  /projects/{id}/download                                                   → bunyan-output.zip
```

`Project`:

```json
{
  "id": "p_123",
  "idea": "…",
  "status": "created | analyzing | awaiting_clarification | awaiting_approval | designing | developing | testing | repairing | documenting | completed | failed",
  "current_agent": "business_analyst | software_architect | developer | qa_tester | project_manager | null",
  "repair_attempt": 0,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "requirements": "RequirementsDocument (full requirements.json) | null",
  "artifacts": [{ "name": "requirements.json", "available": true }],
  "metrics": { "pass_rate": 1.0, "checks_passed": 8, "checks_total": 8, "run_time_seconds": 42 },
  "error": { "code": "out_of_scope", "message": "…" }
}
```

Errors: FastAPI default `{ "detail": "..." }` (string or validation list).

## Open questions

| # | Question | With |
|---|---|---|
| F1 | Final `Project` response shape, status names and payloads above | Alanoud |
| F2 | Out-of-scope rejection: `failed` + `requirements.status == "rejected_out_of_scope"`, or a dedicated `rejected` status? (analyst decision D8) | Alanoud, Ghala |
| F3 | Is `requirements` returned inside `GET /projects/{id}` or fetched as an artifact? | Alanoud |
| F4 | Preview origin: the generated app uses `localStorage`, so the iframe needs `allow-same-origin`; it must be served from a different origin than the frontend | Alanoud |
| F5 | CORS for `http://localhost:5173` | Alanoud |
| F6 | `architecture.json` sample | Naifah |
| F7 | `test_report.json` format and the list of the 8 core checks | Sara |
| F8 | Generated file names (`index.html`, `style.css`, `app.js`) and a sample app for the preview | Yara |
| F9 | Bunyan visual identity: colours, fonts, wireframes (current styles are temporary) | Naifah |

The frontend must never contain LLM API keys; all model calls go through the backend.
