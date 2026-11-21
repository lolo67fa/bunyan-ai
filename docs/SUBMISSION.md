# BUNYAN AI: Submission Package

Tuwaiq Club, King Saud University. Submission date: November 21, 2026.

**Live demo:** https://bunyan-production-dfa4e72b.up.railway.app (open it; no login is needed)

This document says precisely what works, where it runs and how it was verified. Where something
is only in a branch, only mocked, or not built, it says so.

---

## 1. The problem and the product

Small teams and students lose time turning an idea into a working prototype: requirements are
vague, design and code need several skills, documentation is skipped and defects are found late.

BUNYAN AI takes an idea for a simple data-management web app ("manage my inventory: products,
quantities, prices") in Arabic or English and runs it through five agents that work like a small
software team. The user reviews and approves the requirements before anything is built. At the end
the user gets a working app (HTML, CSS, JavaScript, localStorage) to preview and download, with its
requirements, architecture, real browser test results, project plan and risk report.

Scope: CRUD apps with one entity (create, list, search, edit, delete records). Out of scope:
multi-entity apps, server-side databases, logins inside the generated app, payments, native apps.

## 2. The five agents

| # | Agent | Input → output | How it works in this delivery | Owner |
|---|---|---|---|---|
| 1 | Business Analyst | idea (+ answers, + change requests) → `requirements.json` | `llm` mode: Claude `claude-opus-5-5` with a strict Pydantic contract and validation. `mock` mode: deterministic, for the predefined example ideas only. Asks clarification questions, refuses out-of-scope ideas, revises after "request changes". | Ghala |
| 2 | Software Architect | approved requirements → `architecture.json` (contract v0.3.1) | Deterministic. Screens, fields, input controls, validation rules and every error message; messages quoted in acceptance criteria are copied verbatim. | Naifah |
| 3 | Developer | requirements + architecture → `index.html`, `style.css`, `app.js` | Deterministic: a tested CRUD template filled with escaped JSON (no `innerHTML`), RTL/LTR, localStorage. | Yara |
| 4 | QA Tester | the generated app → `test_report.json` | Real Chromium via Playwright, 8 fixed checks: create, list, edit, delete, persistence after refresh, reject incomplete input, empty state, error message visible. Each failure keeps its real error message. | Sara |
| 5 | Project Manager | all outputs + the real QA outcome → `project_plan.md`, `risks.md` | Jood's agent (PR #12) in `mode="rules"` (no paid calls): stages, timeline, real results, open risks. | Jood |

Orchestrator and API (Alanoud, Ghala): `backend/orchestrator/pipeline.py` and `backend/main.py`.

## 3. Workflow

```
idea ─► Business Analyst ─► review in the UI ─┬─ request changes ─► Business Analyst (revision)
                                              ├─ answer questions ─► Business Analyst
                                              └─ approve
                                                   │
        designing ─► Architect ─► developing ─► Developer ─► testing ─► QA (Chromium)
                                                   │
        documenting ─► Project Manager ─► completed ─► preview (sandboxed) + ZIP
```

Status values: `analyzing`, `awaiting_approval`, `awaiting_clarification`, `rejected`, `designing`,
`developing`, `testing`, `documenting`, `completed`, `failed`. A failed stage is reported with its
real reason; QA failures stay visible in the report and in `risks.md`.

**Not delivered: the automatic repair loop** (QA → Developer → QA). It was planned and is not in
the pipeline. The Project Manager states "Automatic repair: not available in this version" and never
claims a repair.

## 4. Technical stack

| Part | Technology |
|---|---|
| Platform UI | React + Vite, Riyadh visual theme (light/dark), Arabic RTL and English LTR, desktop and mobile |
| Backend | Python 3.11, FastAPI, Pydantic contracts per agent |
| LLM | Anthropic Claude `claude-opus-5-5` (Business Analyst `llm` mode only), SDK `anthropic==1.8.0` |
| Generated apps | HTML, CSS, vanilla JavaScript, localStorage |
| QA | Node.js 22, Playwright, Chromium |
| Packaging | One Docker image (frontend build, backend, Node, Chromium), non-root user, `/data` volume |
| Hosting | Railway (trial), HTTPS, persistent volume |
| CI | GitHub Actions (`ci.yml`); manual paid tests in `ba-live-test.yml` |

## 5. What is live, what is only in branches

| Capability | Live on Railway | Branch `delivery/final-submission` (PR to `main`) |
|---|---|---|
| Five-agent pipeline, preview, ZIP | Yes | Yes |
| Business Analyst | **mock** only (no paid calls for guests) | mock and llm (llm needs `BA_MODE=llm` + key) |
| Project Manager | the earlier integration PM (`deploy/club-demo`) | **Jood's PM (PR #12)** with compatibility fixes |
| Architect message mapping for real LLM wording | No (earlier Architect) | Yes (6/7 and 8/8 messages mapped on the two real runs) |
| Guest mode, isolation, quotas, CSRF check, sandboxed preview | Yes | Yes |
| Homepage fix for shared Wi-Fi + Arabic error page | Yes (deployment `f21686ee`, commit `7619e18`) | Yes |
| Automatic repair loop | No | No |

Live deployment: Railway project `bunyan-club-demo`, service `bunyan`, deployment `f21686ee`,
code = commit `7619e18` on branch `deploy/club-demo`. Variables: `BUNYAN_AUTH=guest`,
`BA_MODE=mock`, `BUNYAN_MAX_LLM_ANALYSES_PER_DAY=0`; secrets only in Railway Variables.

## 6. Real-LLM evidence

All paid calls ran in GitHub Actions (`ba-live-test.yml`, manual, confirmation phrase required) with
retries 0, fallbacks off and an output cap of 32,000 tokens. The key is a GitHub secret, never in the app.

| Run | Idea | Requests | Tokens (in / out) | Cost | Result |
|---|---|---|---|---|---|
| 44716341099 | Arabic inventory | 1 | 6,113 / 10,163 | $0.23 | schema-valid, `ready_for_review` |
| 44725920842 | Arabic inventory, full UI journey with one change request | 2 | — | $0.52 | completed, QA passed |
| 44769184001 | Arabic personal library (title, author, category, read date, rating; search by title/author) | 1 | 6,164 / 12,429 | $0.27 | schema-valid, `ready_for_review` |

For run 44769184001 (the requirements file is stored unchanged in
`backend/agents/architect/tests/fixtures/real_llm_library_ar.requirements.json`):

- Model reported by the API: `claude-opus-5-5`; stop reason `end_turn`. The mock analyst does not
  recognise this idea (it returns no entity), so the output can only come from the model.
- Contract: valid `RequirementsDocument`; Arabic; 1 entity `Book`, 5 fields, full CRUD, search on
  title and author; 10 functional requirements, 4 user stories, 21 acceptance criteria
  (create, read, update, delete, validation, persistence); 5 non-blocking clarification questions
  with suggested defaults (categories, rating scale, reading status, sort order).
- Pipeline on that output: Architect valid (0 warnings after the mapping fix) → Developer →
  QA in Chromium **8/8 passed** → Project Manager (Arabic plan and risks) → preview and ZIP served by
  the API (8 files).

## 7. Architect validation gaps (resolved and remaining)

The first real run left 7 validation messages unmapped; the second used different wording and left 8.
Causes: field names written without quotes ("بجانب حقل الكمية"), one "required" message for several
fields, one message for a whole range ("من 2 إلى 100 حرف"), and messages that name their own field
("يجب ألا يتجاوز العنوان 200 حرف"). The Architect now maps all of these (no contract change); regression
tests use both real outputs unchanged.

Remaining: **"must be a whole number"** (`يجب أن تكون الكمية عدداً صحيحاً`). The form already rejects
decimals in integer fields, but the contract (`fields[].messages`) has no slot for that message, so
the app shows the generic Arabic "القيمة غير صحيحة" and the Architect reports the gap as an explicit
warning. **Question for Naifah:** add an optional `invalid` message to `FieldMessages` for number and
select fields (the template already reads it)? It is a contract change, so it was not made before the deadline.

## 8. Security

Details in [DEPLOY.md](../DEPLOY.md). In short:

- Guests get an anonymous identity in a signed (HMAC-SHA256), HttpOnly, Secure, SameSite=Lax cookie.
- Every project has an owner; anyone else gets 404 on every route (API, artifacts, preview, ZIP).
- Writes from other sites are refused (Origin check). Limits per guest, per address and site-wide;
  counters survive restarts. The address comes from the platform proxy, not from client headers
  (tested: spoofed `X-Forwarded-For` does not bypass the limit).
- The public site always loads; only the API needs a new guest identity, so a busy shared Wi-Fi
  cannot lock people out of the homepage. Errors opened in a browser are an Arabic page in the site
  theme; API errors are JSON with `charset=utf-8`.
- Generated apps are untrusted: preview under `Content-Security-Policy: sandbox` with no network
  access; QA runs them on 127.0.0.1 with secrets removed from the environment.
- Guest mode refuses to start with `BA_MODE=llm`: visitors cannot cause paid requests.
- Container: non-root (uid 10001), dropped capabilities, `no-new-privileges`, memory limit.

## 9. Testing evidence

Measured on branch `delivery/final-submission` on November 20, 2026 (local macOS, Python 3.11, Node 22):

| Suite | Result |
|---|---|
| Backend `pytest tests` (API, pipeline, security, guest mode, homepage regression, PM pipeline) | 281 passed |
| Business Analyst `pytest backend/agents/business_analyst` | 298 passed, 10 skipped (9 paid LLM evals are opt-in; 1 needs CrewAI, not installed) |
| Architect | 56 passed |
| Project Manager (Jood's tests + QA-outcome tests) | 56 passed |
| QA Tester (including real Playwright runs) | 11 passed |
| Developer smoke test | PASS |
| React unit tests | 25 / 25 passed |
| React production build | built |
| Docker build + Docker Compose (healthy, guest mode) | passed |
| Browser journeys in Compose: English task manager, Arabic inventory, Arabic bookings (idea → analysis → change request → approval → 4 agents → QA 8/8 → ZIP) | 3 / 3 passed |
| Persistence after container restart; server runs as uid 10001 | passed |
| Riyadh theme light/dark × desktop/mobile: RTL, no horizontal overflow | 4 / 4 passed |
| Live site after the last deploy: homepage 200 UTF-8, health, Arabic 404 page, cross-site write 403, full journey QA 8/8 + ZIP | passed |

CI results for the final commit are on the pull request. The mock analyst's journeys show the change
request honestly as "not applied" (the mock cannot rewrite requirements); the real analyst applied one
in run 44725920842 (the requested supplier-phone field reached the generated app, QA passed).

## 10. Known limitations

- The public demo uses the mock Business Analyst: it handles the example ideas (tasks, inventory,
  appointments/bookings and similar); other ideas get a clarification or refusal. Real analysis needs
  `BA_MODE=llm` with an API key and is not offered to anonymous guests.
- One entity per app; generated apps store data in the browser only.
- No automatic repair loop; no whole-number message slot (see section 7).
- QA uses a fixed set of 8 checks, not one test per acceptance criterion; the report lists verbatim
  messages that the checks did not compare.
- LLM output varies between runs; the Architect reports any message it cannot map instead of dropping it.
- Academic prototype: not for production use. Railway trial resources are limited.

## 11. Team contributions

| Member | Contribution | Pull requests |
|---|---|---|
| Ghala Alshreef (lead) | Business Analyst (mock + LLM, contract, revisions, live tests), integration of all branches, orchestrator hand-offs, Docker/Railway, security and guest mode, delivery | #1, #2, #6, #8, #15, integration and delivery branches |
| Naifah | Software Architect agent and `architecture.json` contract | #4 |
| Yara | Developer agent and the CRUD template | #10 |
| Sara | QA Tester: 8-check Playwright suite and `test_report.json` | #7 |
| Jood | React frontend, Riyadh visual identity and landing page, Project Manager agent | #3, #9, #11, #12, #13, #14 |
| Alanoud | FastAPI backend integration and API tests | #5 |

Every open team PR (#4, #5, #7–#13) is fully contained in the delivery branch (checked with
`git merge-base --is-ancestor`), so authorship history is preserved. Jood's PM (PR #12, commit
`15bfb5e`) was merged unchanged; the compatibility fixes are a separate commit (`92681fb`): an
orchestrator adapter plus small edits so the report never claims repairs, keeps the real QA message,
tells passed/failed/blocked/not_run/skipped apart and shows a run time of 0.

## 12. Rollback

- Live site: Railway → service `bunyan` → Deployments → redeploy an earlier successful deployment
  (the version before the homepage fix was the upload of commit `5c79adb`). Volume and variables are
  not touched by a redeploy.
- Access: set `BUNYAN_AUTH=required` to return to logins (the `BUNYAN_USERS` testers still work).
- Code: `deploy/club-demo` is the deployed code; `main` is unchanged until the delivery PR is merged.

## 13. For reviewers

1. Open the live demo, choose an example ("إدارة المخزون") or type a similar idea, review the
   requirements, optionally request a change, approve, and watch the stages; then open the preview,
   the test report, the plan and the risks, and download the ZIP.
2. Locally: see "Getting Started" in the [README](../README.md) (Docker Compose, no API key needed).
3. Arabic user guide: [user-guide-ar.md](user-guide-ar.md).
