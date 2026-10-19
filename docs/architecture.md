# System Architecture

> **Status:** Proposed architecture for the BUNYAN AI MVP. Details (endpoint names, schema fields) are subject to team agreement during Week 1 and will be updated as implementation progresses.

## 1. Overview

BUNYAN AI converts a natural-language description of a web application into a working CRUD web application, together with requirements, architecture, test results, and project documentation. Five specialized AI agents, orchestrated by CrewAI inside a FastAPI backend, perform the work. A React frontend lets the user submit ideas, approve requirements, follow progress, preview the result, and download all artifacts.

## 2. High-Level Components

```
┌──────────────────────────────────────────────────────────────┐
│                      React Frontend                          │
│  Idea input · Clarification Q&A · Requirement approval ·     │
│  Progress dashboard · App preview (sandboxed) · Download     │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP / JSON (REST API)
┌───────────────────────────▼──────────────────────────────────┐
│                     FastAPI Backend                          │
│  API endpoints · Project/run state · Artifact storage        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Orchestrator (CrewAI)                     │  │
│  │                                                        │  │
│  │  Business Analyst → [User Approval] → Architect →      │  │
│  │  Developer ⇄ QA Tester (max 2 repairs) → Project Mgr   │  │
│  └───────────────┬───────────────────────┬────────────────┘  │
│                  │                       │                   │
│        JSON schemas (contracts)   CRUD template              │
└──────────────────┼───────────────────────┼───────────────────┘
                   │                       │
          ┌────────▼────────┐     ┌────────▼─────────┐
          │  LLM Provider   │     │   Playwright     │
          │ (GPT / Claude)  │     │ (isolated browser│
          │   via API       │     │   contexts)      │
          └─────────────────┘     └──────────────────┘
```

| Component | Location | Responsibility |
|---|---|---|
| React frontend | `frontend/` | All user interaction; never holds API keys. |
| FastAPI backend | `backend/` | Exposes the API, stores run state and artifacts, loads configuration from environment variables. |
| Agents | `backend/agents/` | One module per agent: role, goal, prompt, task definition, expected output. |
| Schemas | `backend/schemas/` | JSON Schemas that define the contracts between agents and between backend and frontend. |
| Orchestrator | `backend/orchestrator/` | CrewAI crew, workflow sequencing, approval pause, repair loop, state tracking. |
| CRUD template | `templates/crud/` | Base HTML/CSS/JS structure the Developer Agent fills in. |
| E2E tests | `tests/e2e/` | Playwright tests for generated apps and for the platform itself. |

## 3. Workflow

**User Idea → Business Analyst → User Approval → Software Architect → Developer → QA Tester → Project Manager → Preview & Download**

| Step | Actor | Input | Output |
|---|---|---|---|
| 1 | User | Natural-language application idea | Idea text |
| 2 | Business Analyst Agent | Idea text (+ answers to clarification questions) | `requirements.json` |
| 3 | User | `requirements.json` shown in the UI | Approval, or edits/feedback |
| 4 | Software Architect Agent | Approved `requirements.json` | `architecture.json` |
| 5 | Developer Agent | `requirements.json`, `architecture.json`, CRUD template | `index.html`, `style.css`, `app.js` |
| 6 | QA Tester Agent | Acceptance criteria, generated app | `test_report.json` |
| 6a | Developer ⇄ QA | Failure report | Revised code + new test report (max 2 times) |
| 7 | Project Manager Agent | All artifacts and run status | `project_plan.md`, `risks.md` |
| 8 | Platform | All artifacts | Live preview + downloadable package |

### 3.1 Scope check

The Business Analyst Agent verifies that the idea fits the CRUD scope. Requests that require out-of-scope features (payments, native mobile apps, enterprise systems, custom backends, authentication) are either reduced to a CRUD equivalent with the user's consent or declined with an explanation.

### 3.2 User approval gate

The workflow pauses after requirements are generated. Nothing is designed or generated until the user approves the requirements. If the user requests changes, the Business Analyst Agent revises `requirements.json` before continuing.

### 3.3 QA ↔ Developer repair loop

```
Developer ──code──► QA Tester ──all tests pass──► Project Manager
    ▲                   │
    └──failure report───┘   (attempts 1 and 2 only)
```

- After the initial generation, QA runs the tests.
- On failure, QA sends a concise failure report (failing test, expected vs. actual behavior, error messages) to the Developer Agent.
- At most **two** repair attempts are made.
- If failures remain, the workflow continues; the final `test_report.json` records the real results and the Project Manager Agent records the open defects as risks.

## 4. Artifacts

| Artifact | Produced by | Format | Content (proposed) |
|---|---|---|---|
| `requirements.json` | Business Analyst | JSON | App name and description, entities with attributes and types, functional requirements, user stories, acceptance criteria, out-of-scope notes. |
| `architecture.json` | Software Architect | JSON | Screens, components per screen, data schema (localStorage keys, fields, validation rules), navigation, behaviors per CRUD operation. |
| `index.html` | Developer | HTML | Application markup. |
| `style.css` | Developer | CSS | Application styles. |
| `app.js` | Developer | JavaScript | CRUD logic, validation, localStorage persistence. |
| `test_report.json` | QA Tester | JSON | Tests executed, pass/fail per test, mapping to acceptance criteria, failure details, repair attempt number. |
| `project_plan.md` | Project Manager | Markdown | Generation summary, deliverables, basic timeline. |
| `risks.md` | Project Manager | Markdown | Identified risks and open issues, including unresolved test failures. |

The exact field definitions will be agreed as JSON Schemas in `backend/schemas/` during Week 1, before agent implementation begins.

## 5. Backend API (proposed)

Final endpoint names and payloads will be defined by the backend owner in agreement with the frontend owners. A possible shape:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/projects` | Submit a new application idea. |
| `GET` | `/projects/{id}` | Get run status and current stage. |
| `POST` | `/projects/{id}/answers` | Submit answers to clarification questions. |
| `POST` | `/projects/{id}/approve` | Approve (or send feedback on) requirements. |
| `GET` | `/projects/{id}/artifacts/{name}` | Retrieve a specific artifact. |
| `GET` | `/projects/{id}/preview` | Serve the generated application for preview. |
| `GET` | `/projects/{id}/download` | Download all artifacts as a ZIP archive. |

## 6. Workflow State

The orchestrator tracks each run through explicit stages, for example:

`created → analyzing → awaiting_clarification → awaiting_approval → designing → developing → testing → repairing (1..2) → documenting → completed | failed`

The frontend dashboard reads this state to show progress.

## 7. Security Considerations

- LLM API keys are read from environment variables on the backend only (see `.env.example`).
- Generated code is treated as untrusted: previewed in a sandboxed iframe and tested in isolated Playwright browser contexts.
- Tests use synthetic data only.
- The repair loop is capped at two attempts.
- The platform is an academic prototype and is not intended for production deployment.

## 8. Language Models

Agents use pretrained large language models (GPT or Claude) through provider APIs. No custom model training or large training dataset is required. Reliability comes from structured prompts, JSON schema validation of agent outputs, the reusable CRUD template, and automated testing.
