# Contribution Audit: Ghala Alshreef

Evidence ledger for the contributions of **Ghala Alshreef** (GitHub `lolo67fa`), founder and team
lead of BUNYAN AI, from the first commit (October 20, 2026) to the final release (`main` @
[`296099e`](https://github.com/lolo67fa/bunyan-ai/commit/296099e), November 21, 2026) and the
follow-up [PR #17](https://github.com/lolo67fa/bunyan-ai/pull/17), merged into `main` as
[`fdcef1d`](https://github.com/lolo67fa/bunyan-ai/commit/fdcef1d) on November 21, 2026.

It supports the "Team & Contributions" section of the [README](../README.md). Every entry names
the commits, pull requests, tests or deployments it rests on.

---

## 1. Method and sources

| Source | What was checked |
|---|---|
| Git history, all refs | 92 commits on every remote branch (84 on `main`), authors, committers, merges, `Co-Authored-By` trailers, files changed per commit |
| `git blame` of `main` @ `296099e` | Who last wrote each line of the delivered code, per area (section 5). This measures the final code, not effort. |
| GitHub pull requests #1–#18 | Author, merger, dates and size of each PR; who opened and merged it |
| GitHub Actions | Who triggered each run (CI, and the manual paid Business Analyst tests) |
| Railway | Deployment history of the service `bunyan` (project `bunyan-club-demo`) |
| Claude Code session history on the lead's computer | The instructions Ghala gave in three local sessions: Nov 4, Nov 11–19, and Nov 7–21 (sections 6 and 7) |
| Repository documents | `docs/team-roles.md` (the original assignments), `README.md`, `DEPLOY.md`, `docs/SUBMISSION.md` |

**Confidence levels used below:**

- **Verified:** the commit, PR, workflow run or deployment exists and was checked.
- **Partially verified:** the result is verified, but the exact division of work is not fully documented.
- **Unverified:** nothing in the available sources confirms it.

### How the work was done

Much of Ghala's implementation from November 11 onward was carried out with **Claude Code**, an AI
coding tool, under her direction. She defined each task and its constraints, decided on scope and
trade-offs, approved merges, deployments and paid calls, and verified the results. Commits made this
way carry a `Co-Authored-By: Claude` trailer, and the ledger marks them **"AI-assisted under Ghala's
direction"**.

Commits without the trailer (the October–early November Business Analyst work) are marked only by
their author; no claim is made about how they were written. Claude Code is a tool, not a team
member. The team is six people.

**Not available:**

- Sessions before November 4 (repository setup on Oct 20, Business Analyst work Oct 25–Nov 1) are not
  on this computer. Those contributions rest on commits and PRs only.
- Commit [`d46a166`](https://github.com/lolo67fa/bunyan-ai/commit/d46a166) ("Architect v0.3.1") came
  from a cloud Claude Code session that is not accessible, so **who started it cannot be verified**.
  It is left with Naifah's PR #4 and is not credited to Ghala.
- No GitHub issues exist. PR reviews were not done through GitHub's review feature (Ghala left 3 PR
  comments, on #2 and #6). Review and decision work is documented by the merges and by session
  instructions.

---

## 2. Summary of verified contributions

| # | Area | Ghala's role | Key evidence | Confidence |
|---|---|---|---|---|
| A | Project initiation, scope, team structure, collaboration rules | Founder and author | PR #1 (`9422dfe`): README, `docs/architecture.md`, `docs/team-roles.md`, `docs/development-plan.md`, `docs/github-workflow.md`, PR template | Verified |
| B | Business Analyst Agent (original component) | Owner and author | PRs #2, #6, #8, #15; 6,414 lines of `backend/agents/business_analyst` on `main` | Verified |
| C | Orchestrator (pipeline, QA stage, state, persistence) | Implemented (AI-assisted under her direction) | `15f6b9a`, `2e61684`, `c097bf8`; all 735 lines of `backend/orchestrator` | Verified |
| D | Integration of the other five components | Integrator, reviewer, merger | `fdeb8d6`…`744223d`, `90e7d87`, `92681fb`, PR #14 merge, PR #16 | Verified |
| E | Backend API extension and frontend–backend connection | Implemented (AI-assisted) on top of Alanoud's and Jood's work | `2e61684`, `9636cc5`, `a3767a8`, `bf6f1d2`; 543 of 624 lines of `backend/main.py` | Verified |
| F | QA integration and test infrastructure | Implemented (AI-assisted); Sara owns the QA agent | `c097bf8` (`qa_stage.py`, 705-line test suite), `8bfd313`; 3,346 lines in `tests/` | Verified |
| G | Project Manager: interim agent, then integration of Jood's agent | Interim author; integrator of Jood's agent | `d5da5a9` (interim, later removed), `90e7d87`, `92681fb`, `5eab528` | Verified |
| H | Docker, Railway, CI/CD, production release | Implemented and operated | `f895495`, `245dd64`, `railway.json`, `DEPLOY.md`; Railway deployments; 33 CI runs and 5 paid-test runs triggered | Verified |
| I | Security and guest access | Implemented (AI-assisted) | `f895495`, `5c79adb`, `858ce45`, `7619e18`; `backend/security.py` (385 lines) | Verified |
| J | Production debugging (Safari 429, UTF-8, QA port, preview CSP) | Diagnosed and fixed (AI-assisted) | `858ce45`, `7619e18`, Railway logs, deployment `f21686ee` | Verified |
| K | Real-LLM verification and cost control | Designed the safeguards, approved each paid run | Workflow runs 42211456095, 44716341099, 44725920842, 44769184001 | Verified |
| L | Final delivery and release | Release manager | PR #16 (`296099e`), `docs/SUBMISSION.md`, `docs/user-guide-ar.md`, Railway deployment `9e873d4b` | Verified |
| M | Post-release capabilities: deterministic repair loop, protected real BA access, integer validation message (Architect contract v0.3.2) | Specified, decided and approved; implemented (AI-assisted under her direction) | PR #17, merged as `fdcef1d` (section 3.M) | Verified |

---

## 3. Evidence ledger by category

Commit links: `https://github.com/lolo67fa/bunyan-ai/commit/<sha>`; PR links: `https://github.com/lolo67fa/bunyan-ai/pull/<n>`.

### A. Project initiation and leadership

| Date | Contribution | Ghala's role | Files | Commits / PRs | Confidence |
|---|---|---|---|---|---|
| Oct 20 | Created the repository and its foundation: project definition, problem statement, objectives, CRUD scope and exclusions, the five-agent architecture, workflow with user approval, technology stack, roadmap, team roles, GitHub collaboration rules | Author (the setup commit carries the AI trailer: AI-assisted under her direction) | `README.md`, `docs/architecture.md`, `docs/team-roles.md`, `docs/development-plan.md`, `docs/github-workflow.md`, `.github/PULL_REQUEST_TEMPLATE.md`, component READMEs, `.gitignore`, `.env.example` (15 files, +1,302) | `b5fc257`, [`9422dfe`](https://github.com/lolo67fa/bunyan-ai/commit/9422dfe), [PR #1](https://github.com/lolo67fa/bunyan-ai/pull/1) | Verified |
| Oct 20 to Nov 21 | Assigned the six roles and agent ownership, and kept the shared documentation | Team lead | `docs/team-roles.md` (only author), `README.md` (all edits on `main`) | git history of those files | Verified |
| Nov 7 | Integration-readiness review after Alanoud and Jood reported their work complete | Requested and decided | session instruction, Nov 7 | (decision, no commit) | Partially verified |
| Nov 11 | Merge plan for six open PRs (#4, #5, #7, #8, #9, #10), then the decision to integrate them herself on a dedicated branch | Lead and integrator | branch `feature/ghala-full-integration` | `fdeb8d6`…`744223d` | Verified |
| Nov 19 | Full repository audit; decision on PM ownership; decision to adopt the Riyadh visual identity from Jood's PR #13 | Decision-maker | session instructions, Nov 19 | followed by Jood's PR #14 and `90e7d87`/`92681fb` | Verified |
| Nov 20–21 | Final execution plan: protect the working version, then guest mode, PM adoption, real-BA verification, acceptance tests, final PR and delivery package | Release manager | session instructions | PR #16, deployments | Verified |
| All PRs | Merged 13 of the 14 merged PRs (#1, #2, #4–#10, #12, #14–#16; #3 was merged by Alanoud) | Maintainer | — | GitHub PR metadata | Verified |

### B. Business Analyst Agent (Ghala's original component)

| Date | Contribution | Files | Commits / PRs | Tests | Confidence |
|---|---|---|---|---|---|
| Oct 25 | BA agent with the provisional `requirements.json` contract: Pydantic `RequirementsDocument`, prompts, mock analyst, CrewAI backend, samples, tests | `backend/agents/business_analyst/**` (36 files, +5,474) | [`917152e`](https://github.com/lolo67fa/bunyan-ai/commit/917152e) | included | Verified |
| Oct 26 | Direct Anthropic SDK backend, Gulf-dialect sample, integration guide for the Architect; CrewAI and older-SDK compatibility | `direct_llm.py`, `contract/INTEGRATION.md` | `69ac7aa`, `8d58aa8` | included | Verified |
| Nov 1 | Hardened input contract, scope guard (refuses out-of-scope ideas), Architect handoff, evaluation scenarios A–C | 24 files (+2,282 / −483) | `518d7da` | included | Verified |
| Nov 1 | One-call cost controls (no retries, no fallbacks) and a live-test runner; manual GitHub Actions workflow that needs a typed confirmation before any paid call | `live_check.py`, `.github/workflows/ba-live-test.yml` | `d9fccc9`, `f45f1f1`; [PR #2](https://github.com/lolo67fa/bunyan-ai/pull/2) (+8,946), [PR #6](https://github.com/lolo67fa/bunyan-ai/pull/6) | workflow | Verified |
| Nov 4–6 | Fixed the AC-2 conflict Sara reported (required fields with a default must not be expected to fail when empty) | 13 files | [`cc8c80d`](https://github.com/lolo67fa/bunyan-ai/commit/cc8c80d), [PR #8](https://github.com/lolo67fa/bunyan-ai/pull/8) | BA tests | Verified (Nov 4 session) |
| Nov 6 | First real-model test in GitHub Actions: the confirmation guard refused the first run (no call); the second passed | — | runs 42211109903, 42211456095 (5,984 / 12,263 tokens, $0.27) | live summary | Verified |
| Nov 20 | Real LLM mode inside the app: background analysis, honest revision reporting, safe user-facing errors, frontend states; 32,000-token output cap; live UI journey with one paid revision | 22 files | [`bf6f1d2`](https://github.com/lolo67fa/bunyan-ai/commit/bf6f1d2), `38ee432`, `6f6cd8e`, `62ecfa6`, [PR #15](https://github.com/lolo67fa/bunyan-ai/pull/15) | runs 44716341099 ($0.23), 44725920842 (journey, $0.52) | Verified |
| Nov 20 | Library idea through the real model, then the full pipeline offline (QA 8/8) | — | run 44769184001 (6,164 / 12,429 tokens, $0.27) | `tests/` fixtures | Verified |

On `main`: 6,414 lines of `backend/agents/business_analyst`, all by Ghala (`git blame`); 298 BA tests pass, plus 10 opt-in tests skipped.

### C. Multi-agent orchestration

The orchestrator was originally assigned to Alanoud (`docs/team-roles.md`). The delivered orchestrator
was implemented by Ghala, AI-assisted under her direction.

| Date | Contribution | Files | Commits | Tests | Confidence |
|---|---|---|---|---|---|
| Nov 11 | MVP pipeline: approved requirements → Architect → Developer → stored app; status transitions; error codes; output checks | `backend/orchestrator/pipeline.py`, `__init__.py`, `tests/test_pipeline.py` | [`15f6b9a`](https://github.com/lolo67fa/bunyan-ai/commit/15f6b9a) | 25 tests | Verified |
| Nov 11 | Run the pipeline when the user approves, in the background, with recovery of interrupted projects | `backend/main.py`, tests | [`2e61684`](https://github.com/lolo67fa/bunyan-ai/commit/2e61684) | API tests | Verified |
| Nov 11 | QA stage: one QA run at a time (thread and file lock), evidence copied into the project, server paths removed, outcomes passed / failed / blocked / not_run, metrics | `backend/orchestrator/qa_stage.py` | [`c097bf8`](https://github.com/lolo67fa/bunyan-ai/commit/c097bf8) | `tests/test_qa_pipeline.py` (705 lines, including real Playwright) | Verified |
| Nov 12 | PM stage after QA (first with an interim agent) | `pipeline.py` | `d5da5a9` | `tests/test_pm_pipeline.py` | Verified |
| Nov 20 | QA receives `architecture.json`; an Architect crash is flagged before approval | `pipeline.py`, `main.py` | `8bfd313` | tests | Verified |
| Nov 21 | Repair loop Developer → QA → repair → QA re-test, at most 2; `repair_history.json` (PR #17, merged) | `pipeline.py`, `qa_stage.py`, `developer/repair.py` | `f674274` | `tests/test_repair_loop.py` (13, including real Chromium) | Verified |

All 735 lines of `backend/orchestrator` at the release (`296099e`) are Ghala's, and all 839 after PR #17 (`git blame`).

### D. Integration of the other members' agents

| Component (owner) | What Ghala did | Evidence | Confidence |
|---|---|---|---|
| Architect (Naifah, PR #4) | Integrated it into the integration branch, connected it in the pipeline, fixed compatibility with real LLM wording (validation messages the Architect could not map: 7, then 8 → 0); (PR #17) optional `messages.invalid` (contract v0.3.2) | `ef6ca83`, [`19d12a3`](https://github.com/lolo67fa/bunyan-ai/commit/19d12a3), `dd85398`, `4a9f4fd`; 151 of 2,735 Architect lines | Verified |
| Developer (Yara, PR #10) | Integrated it and used it as the Developer stage; one-line fallback in the template | `6832881`, `19d12a3` (`templates/crud/app.js`) | Verified |
| QA (Sara, PR #7) | Integrated it; QA stage, locking, evidence, report validation; port and secret isolation in Docker | `188e470`, `c097bf8`, `f895495` (`runner.py`: 6 lines) | Verified |
| Frontend (Jood, PRs #3/#9) | Integrated PR #9; connected the React app to the real API | `7637849`, [`a3767a8`](https://github.com/lolo67fa/bunyan-ai/commit/a3767a8) | Verified |
| Backend API (Alanoud, PR #5) | Integrated it, resolving the `ci.yml` conflict, and extended it (see E) | `744223d` | Verified |
| Project Manager (Jood, PR #12) | Tested it independently (found 4 accuracy issues), merged it unchanged, then made separate compatibility fixes and an adapter (see G) | `90e7d87`, `92681fb` | Verified |
| Riyadh theme (Jood, PRs #13/#14) | Decided to adopt it, reviewed and merged PR #14, tested light/dark and mobile/desktop | `7178568`; Docker and live checks | Verified |
| All components | Final reconciliation of every branch into one delivery PR; every open team PR was confirmed to be fully contained (`git merge-base --is-ancestor`) | [PR #16](https://github.com/lolo67fa/bunyan-ai/pull/16), merge `296099e` (237 files) | Verified |

### E. Backend and frontend integration

Alanoud wrote the original FastAPI application, Pydantic API contracts, JSON storage, BA endpoint and
first CI (PR #5). Ghala extended it:

| Date | Contribution | Files | Commits | Confidence |
|---|---|---|---|---|
| Nov 11 | Approval starts generation; status and project state for the frontend | `backend/main.py` | `2e61684` | Verified |
| Nov 11 | Artifacts, sandboxed preview and ZIP download endpoints (fixed file list, project-folder resolution) | `backend/artifacts.py` (all 89 lines), `main.py` | [`9636cc5`](https://github.com/lolo67fa/bunyan-ai/commit/9636cc5) | Verified |
| Nov 12 | React frontend against the real FastAPI backend: HTTP client, status polling, Arabic and English journeys | `frontend/src/api/httpClient.js` and screens (8 frontend files; 11 files, +2,138 in total) | [`a3767a8`](https://github.com/lolo67fa/bunyan-ai/commit/a3767a8) | Verified |
| Nov 20 | Real-LLM analysis states and safe errors in the UI | 6 frontend files | `bf6f1d2` | Verified |
| Nov 20 | Same-origin serving of the built frontend, health route | `main.py` | `f895495` | Verified |

On `main`, `backend/main.py` is 543 lines by Ghala and 81 by Alanoud. Jood's Riyadh redesign (PR #14)
later rewrote most screens while keeping the integration ("Keep the integration fixes in the new
project screens", `5db2cc1` by Jood), so `frontend/src` is 7,740 lines by Jood and 138 by Ghala.

### F. QA and testing infrastructure

| Contribution | Evidence | Confidence |
|---|---|---|
| Connected Sara's QA agent to the pipeline; real Playwright runs in Arabic and English scenarios; a test that breaks persistence on purpose and checks the real suite catches it | `c097bf8`, `tests/test_qa_pipeline.py` | Verified |
| Backend test suites for the pipeline, API alignment, artifacts, security, guest mode, homepage, PM pipeline | 3,346 lines in `tests/` (Ghala), alongside Sara's 1,019 and Alanoud's 244 | Verified |
| CI: QA, pipeline, security and guest tests in `ci.yml`; runs on `deploy/**` | `.github/workflows` 262 of 291 lines; `245dd64` | Verified |
| Browser journey script for the real UI (idea → analysis → change request → approval → 4 agents → ZIP), used locally, in Docker and on the live site | `tests/e2e/live/journey.mjs` (`6f6cd8e`, `f895495`) | Verified |
| Acceptance runs: Docker journeys EN / AR / bookings 3/3; live journeys; theme and mobile checks 4/4 | `docs/SUBMISSION.md` §9 | Verified |

Sara owns the QA agent: the 8-check suite, `tests/e2e/lib` and `specs`, and the report contract (740 lines of `tests/e2e` plus 411 of 417 lines of `backend/agents/qa_tester`).

### G. Project Manager

| Date | Contribution | Commits | Confidence |
|---|---|---|---|
| Nov 12 | Interim rules-based PM so the five-agent pipeline worked end to end before PR #12 was ready | [`d5da5a9`](https://github.com/lolo67fa/bunyan-ai/commit/d5da5a9) (superseded: removed in `92681fb`) | Verified |
| Nov 19 | Independent test of Jood's PR #12; found four accuracy issues: claimed repairs that did not happen, lost QA messages, QA states merged, a run time of 0 hidden | Nov 19 session; reported to the team | Verified |
| Nov 20 | Merged PR #12 unchanged (`15bfb5e`), then a separate commit with an orchestrator adapter (`mode="rules"`, no paid call), the fixes for those four issues, and 7 new tests | [`90e7d87`](https://github.com/lolo67fa/bunyan-ai/commit/90e7d87), [`92681fb`](https://github.com/lolo67fa/bunyan-ai/commit/92681fb) | Verified |
| Nov 21 | PM reports the real repair history, as a separate commit; Jood's samples unchanged (PR #17, merged) | `5eab528` | Verified |

Jood owns the PM agent: 1,577 of 1,740 lines of `backend/agents/project_manager` on `main`. Ghala's 163 lines are the compatibility fixes.

### H. Infrastructure, DevOps and deployment

| Date | Contribution | Evidence | Confidence |
|---|---|---|---|
| Nov 20 | One Docker image: React build, FastAPI, Node 22, Playwright Chromium; non-root user (uid 10001); entrypoint that drops privileges; `/data` volume; health check. Compose with dropped capabilities, `no-new-privileges` and memory limits. `railway.json`, `deploy.env.example`, `DEPLOY.md` | [`f895495`](https://github.com/lolo67fa/bunyan-ai/commit/f895495) (all Dockerfile, compose, docker, railway.json and DEPLOY.md lines) | Verified |
| Nov 20 | Railway: project `bunyan-club-demo`, service `bunyan`, 500 MB volume at `/data`, public domain, variables and secrets (values only in Railway), 11 login accounts for rollback | Railway deployment history (Nov 20–21) | Verified |
| Nov 20–21 | Deployments: guest mode (`85dabb51`), homepage fix (`52ff3d8d`, `f21686ee`), final `main` (`9e873d4b`); rollback point recorded before each change | Railway deployment list | Verified |
| Nov 1–21 | CI: added the paid-test workflow, extended `ci.yml` (pipeline, QA, security and guest tests; `deploy/**` branches) | `f45f1f1`, `245dd64`; 33 of 71 CI runs triggered by `lolo67fa` | Verified |
| Nov 21 | Production release of `main` @ `296099e`: clean-checkout image build, smoke tests, deployment, live verification (old projects and cookies intact, isolation, CSRF, Arabic errors, AR/EN QA 8/8, theme 4/4) | deployment `9e873d4b` | Verified |

### I. Security and guest access

| Contribution | Evidence | Confidence |
|---|---|---|
| Login mode: HTTP Basic with PBKDF2 hashes, brute-force limit, per-project owner (404 for everyone else on every route), per-user and site-wide quotas stored across restarts, LLM daily cap and concurrency | `f895495`, `backend/security.py`, `tests/test_club_security.py` (16) | Verified |
| Sandboxed preview (CSP `sandbox`, no network), QA process without secrets, QA port isolated from the web server | `f895495` | Verified |
| Guest mode: signed anonymous sessions (HMAC-SHA256; HttpOnly, Secure, SameSite=Lax), per-guest, per-address and site-wide limits, limit on new sessions per address, Origin check against cross-site writes, refusal to start with a paid analyst for guests | [`5c79adb`](https://github.com/lolo67fa/bunyan-ai/commit/5c79adb), `tests/test_guest_mode.py` (18) | Verified |
| Live checks: spoofed `X-Forwarded-For` cannot bypass the per-address limit; isolation between guests; forged cookie → 404; cross-site POST → 403 | the Nov 20 session and Railway logs | Verified |
| Protected real analyst for guests: hashed access codes, per-code and site caps, daily USD budget reserved before each request (PR #17, merged; off by default) | `e29b106`, `tests/test_llm_access.py` (17) | Verified |

### J. Production debugging

| Issue | Diagnosis | Fix | Evidence |
|---|---|---|---|
| Safari showed raw JSON with garbled Arabic instead of the site | Railway logs showed `GET /` → 429 for one address: cookieless page loads used up the new-guest budget, the error was JSON, and JSON had no charset | The site always loads; only the API needs a new guest. Arabic error page in the Riyadh theme; `charset=utf-8` on JSON | [`858ce45`](https://github.com/lolo67fa/bunyan-ai/commit/858ce45), [`7619e18`](https://github.com/lolo67fa/bunyan-ai/commit/7619e18), `tests/test_guest_homepage.py` (6), deployment `f21686ee` |
| QA blocked inside Docker | the suite read `PORT`, the web server's port | dedicated `BUNYAN_QA_PORT` | `f895495`, test |
| Preview assets blocked under the CSP sandbox | `'self'` does not match an opaque origin | explicit request origin | `f895495` |
| Real-LLM validation wording not mapped by the Architect | see D | `19d12a3`, `dd85398` | regression tests on real outputs |

### K. Real-LLM verification and cost control

| Run | Date | Purpose | Result |
|---|---|---|---|
| 42211109903 | Nov 6 | Confirmation guard check | refused, no API call |
| 42211456095 | Nov 6 | First real analysis | passed, 5,984 / 12,263 tokens, $0.27 |
| 44716341099 | Nov 20 | One call, Arabic inventory | passed, $0.23 |
| 44725920842 | Nov 20 | Full UI journey with one revision (2 requests) | passed; the requested field reached the app; QA passed; $0.52 |
| 44769184001 | Nov 20 | One call, personal-library idea | passed, 6,164 / 12,429 tokens, $0.27; full pipeline offline QA 8/8 |

All five were triggered by `lolo67fa`, each after an explicit decision. Safeguards: typed confirmation, retries and fallbacks off, output cap, key only in GitHub secrets.

### L. Final delivery

| Contribution | Evidence | Confidence |
|---|---|---|
| Delivery branch reconciling all work; final PR into `main` with CI green; merge commit that keeps every author's history (no rewrite) | [PR #16](https://github.com/lolo67fa/bunyan-ai/pull/16), `296099e` | Verified |
| Submission documentation: README status, `docs/SUBMISSION.md` (live vs branch, evidence, limitations, rollback), Arabic user guide, deployment guide | [`1ef728d`](https://github.com/lolo67fa/bunyan-ai/commit/1ef728d) | Verified |
| GitHub `main` and Railway run the same code | deployment `9e873d4b` built from a clean checkout of `296099e` | Verified |

### M. PR #17: repair loop, protected real BA access, integer validation (merged Nov 21)

[PR #17](https://github.com/lolo67fa/bunyan-ai/pull/17): 38 files, +1,496 / −99. Opened and merged by
`lolo67fa` (merge `fdcef1d`), CI green on head `be2e6c6`. AI-assisted under Ghala's direction (all
six commits carry the trailer).

**Ghala's instruction (Nov 21).** Finish the remaining engineering work and verify that the whole team
deliverable is on GitHub. Her constraints:
- no paid calls without approval;
- production stays in mock mode;
- no merge or deployment without approval;
- no breaking contract change without coordinating with Naifah;
- never fabricate test results or claim a repair that did not change code;
- regression tests for every case.

**Technical decisions, taken within those constraints and approved when she merged:**

| Decision | Why | Where |
|---|---|---|
| Repair strategy is **deterministic** (`restore_from_contracts`): rebuild the app from the approved contracts and replace every generated file that differs; no LLM | Real repairs without paid calls or new secrets; an LLM repair would have needed a separately approved provider setup | `backend/agents/developer/repair.py` (63 lines added next to Yara's 39) |
| A repair counts only if a file changed; then QA re-tests in real Chromium (attempts 1 and 2); otherwise the loop stops (`no_change`) | No claimed repair without a real change and a real re-test | `backend/orchestrator/pipeline.py`, `qa_stage.py` (the report's attempt must match) |
| Save `repair_history.json` and the first failing report `test_report.initial.json`; serve and zip them | The original failure and every step stay inspectable | `backend/artifacts.py` |
| Jood's PM gets an optional `repair_history` input; without it her agent behaves as before | Accurate reports without changing her samples or her tests | `5eab528` (separate commit, her samples byte-identical) |
| Older test suites run with `BUNYAN_REPAIR=off`; new suites cover the loop | Existing tests keep checking the no-repair path | `tests/conftest.py`, `tests/test_repair_loop.py` |
| Real BA for guests only through **access codes**; `BA_MODE` stays `mock`; off by default | The public site cannot spend money; the key and codes stay in platform variables | `backend/llm_access.py` (287 lines) |
| Spending checked **before** a request: per code per day (3), site-wide per day, one at a time, daily USD budget (2) that reserves the worst case (0.72 USD) and then books the real usage | The budget cannot be exceeded, even with requests in flight | `backend/llm_access.py`, `direct_llm.py` usage hook |
| The server refuses to start unless retries, SDK retries and fallbacks are off, the output cap is ≤ 32,000 and the backend is direct | Unsafe settings fail loudly instead of costing money | `llm_access.check_configuration` |
| Integer message as an **optional** `fields[].messages.invalid` (number and select fields only), `schema_version` unchanged | Backwards compatible; the template already read it; documented for Naifah | `backend/agents/architect/schema.py`, `from_requirements.py`, `contract/CONTRACT.md` ("Addition in v0.3.2") |

**Commits:**

| Commit | Content |
|---|---|
| [`4a9f4fd`](https://github.com/lolo67fa/bunyan-ai/commit/4a9f4fd) | Architect v0.3.2 `messages.invalid`, regenerated JSON schema, schema, conversion and browser tests |
| [`5eab528`](https://github.com/lolo67fa/bunyan-ai/commit/5eab528) | Jood's PM reports the real repair history |
| [`f674274`](https://github.com/lolo67fa/bunyan-ai/commit/f674274) | Repair loop in the orchestrator |
| [`3421a2b`](https://github.com/lolo67fa/bunyan-ai/commit/3421a2b) | Tests view shows the repair history |
| [`e29b106`](https://github.com/lolo67fa/bunyan-ai/commit/e29b106) | Protected real BA: backend, endpoints, access-code box in the UI |
| [`be2e6c6`](https://github.com/lolo67fa/bunyan-ai/commit/be2e6c6) | Docs: README, SUBMISSION, architecture, DEPLOY, Developer and QA READMEs |

**Tests and verification:**
- Local: backend 315 passed; Architect 60; PM 56; BA 298 (+10 opt-in skipped); QA 11; React 26/26 and production build.
- Repair loop: 13 tests, including real Chromium in English and Arabic (QA finds the defect, the repair changes `app.js`, the re-test passes 8/8).
- Protected BA: 17 tests, replaying the real output of paid run 44769184001 through a stand-in client. No network, no new paid call.
- Integer message: 4 tests in real Chromium. "2.5" in «الكمية» shows «يجب أن تكون الكمية عدداً صحيحاً»; decimals are still accepted.
- Docker image: journeys EN / AR / bookings 3/3, and a real repair on the real-LLM library app (7/8 → `app.js` restored → 8/8).

**Approval and status:**
- Merged by Ghala on Nov 21 ("Merge both").
- **Not deployed:** production is still `main` @ `296099e` (deployment `9e873d4b`), with mock mode and the access codes off. Deploying is a separate decision.

---

## 4. Claude Code sessions: instructions and outcomes

Only Ghala's instructions are summarised. No session content, credentials or tokens are reproduced.

| Session date | Instruction (summary) | Result | Evidence |
|---|---|---|---|
| Nov 4 | Review the BA agent for the AC-2 conflict Sara reported | fixed | `cc8c80d`, PR #8 |
| Nov 7 | Review integration readiness after Alanoud and Jood reported completion | readiness review (no code) | — |
| Nov 11 | Prepare a safe merge plan for PRs #4, #5, #7, #8, #9, #10 | plan; then integrated locally | `fdeb8d6`…`744223d` |
| Nov 11 | Step 1: integration workspace (approved resolving the `ci.yml` conflict) | done | `744223d` |
| Nov 11 | Step 2: MVP orchestrator | done, 25 tests | `15f6b9a` |
| Nov 11 | Step 3: connect the orchestrator to FastAPI | done | `2e61684` |
| Nov 11 | Step 4: artifacts, preview and download | done | `9636cc5` |
| Nov 11 | Step 5: integrate the QA agent | done | `c097bf8` |
| Nov 12 | Step 6A: real frontend–backend integration | done | `a3767a8` |
| Nov 12 | Step 6B: Project Manager agent in the pipeline | done (interim, later replaced) | `d5da5a9` |
| Nov 13 | Back up the integration branch to GitHub | pushed | `feature/ghala-full-integration` |
| Nov 19 | Final repository audit and MVP readiness | audit | — |
| Nov 19 | Independently test Jood's PM (PR #12) | 4 issues found | — |
| Nov 19 | PM integration decision; adopt the Riyadh visual identity | decisions; PR #14 by Jood | `7178568` |
| Nov 20 | Review PR #14 against the integration branch | merged | `7178568` |
| Nov 20 | Fix and enable the real BA in the app | done | PR #15 |
| Nov 20 | Docker and club-demo deployment (trial plan, mock, one test account first, secrets only in Railway) | done | `f895495`, Railway |
| Nov 20 | Public guest access without login | done after approval | `5c79adb`, deployment `85dabb51` |
| Nov 20 | Final execution and delivery: PM adoption, Architect gaps, acceptance tests, final PR, docs | done | `90e7d87`, `92681fb`, `19d12a3`, `dd85398`, PR #16 |
| Nov 20 | Urgent: Safari shows raw JSON | fixed, deployed after approval | `858ce45`, `7619e18`, `f21686ee` |
| Nov 21 | Merge the final PR; deploy final `main` | done | `296099e`, `9e873d4b` |
| Nov 21 | Remaining features: repair loop, protected real BA, integer message; keep production in mock mode; no paid calls; no merge or deploy without approval | done; PR #17 opened, CI green | PR #17 |
| Nov 21 | "Merge both" (PRs #17 and #18) | merged | `fdcef1d`, `93086d2` |

---

## 5. Team: original assignment and delivered work

Line counts are `git blame` of `main` @ `296099e`: who last wrote each line of the delivered code.
They are a measure of final code, not of effort, design or review.

| Member | Original assignment (`docs/team-roles.md`) | Delivered (verified) | PRs |
|---|---|---|---|
| **Ghala Alshreef** | Business Analyst, team lead, docs | Business Analyst (6,414 lines); orchestrator (735 at the release, 839 after PR #17); repair loop, protected real BA access and integer message (PR #17); most of the backend API layer (`main.py` 543, `security.py` 385, `artifacts.py` 89); integration of every component; Docker, Railway, CI, security, guest mode; release and docs | #1, #2, #6, #8, #15, #16, #17, #18 |
| **Naifah** | Software Architect, frontend UI/UX | Software Architect agent and `architecture.json` contract v0.3.0 (2,495 lines of `backend/agents/architect`) | #4 |
| **Yara** | Developer Agent, CRUD template | Developer agent and the CRUD template (all of `backend/agents/developer`; 129 of 152 lines of `templates/crud`), CI smoke test | #10 |
| **Sara** | QA Tester | 8-check Playwright suite, QA agent, `test_report.json` contract, QA v0.2; reported the AC-2 conflict | #7 |
| **Jood** | Project Manager, React frontend | React frontend (7,740 lines of `frontend/src`), API alignment, visual identity, Riyadh landing and platform theme, Project Manager agent (1,577 lines) | #3, #9, #11, #12, #13, #14 |
| **Alanoud** | Backend, orchestration, GitHub Actions | FastAPI application, Pydantic API contracts, JSON storage, BA endpoint, input validation, first CI pipeline (`backend/schemas` 64 of 79 lines) | #5 |

After PR #17 (`main` @ `93086d2`), the `git blame` figures that changed:

| Area | Lines on `main` |
|---|---|
| `backend/orchestrator` | Ghala 839 |
| `backend/main.py` | Ghala 596, Alanoud 81 |
| `backend/llm_access.py` (new) | Ghala 287 |
| `backend/agents/developer/repair.py` | Yara 39, Ghala 63 |
| `backend/agents/project_manager` | Jood 1,577, Ghala 203 |
| `backend/agents/architect` | Naifah 2,495, Ghala 231, and 89 from the unattributed `d46a166` |
| `tests/` | Ghala 3,869, Sara 1,019, Alanoud 244, Yara 31 |
| `frontend/src` | Jood 7,737, Ghala 261 |

Ownership that changed:

- **Orchestration and much of the backend:** assigned to Alanoud, delivered by Ghala on top of Alanoud's FastAPI base.
- **Frontend UI/UX:** listed for Naifah, delivered by Jood.

Nothing in this ledger reassigns another member's component to Ghala. Integration and
compatibility work on those components is listed as such.
