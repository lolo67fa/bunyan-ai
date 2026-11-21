# BUNYAN AI

### Multi-Agent AI Platform for Building CRUD Web Applications

**Tuwaiq Club — King Saud University**

> **Status (November 20, 2026): delivered MVP.** All five agents, the orchestrator, the Riyadh-themed React
> platform and a Docker/Railway deployment are implemented and tested.
>
> **Live demo:** https://bunyan-production-dfa4e72b.up.railway.app (guest access, no login; mock Business Analyst)
>
> Submission package: [docs/SUBMISSION.md](docs/SUBMISSION.md) (what is live, what is only in branches,
> real-LLM evidence, test results, limitations, team contributions, rollback). Arabic user guide:
> [docs/user-guide-ar.md](docs/user-guide-ar.md). Deployment and security: [DEPLOY.md](DEPLOY.md).

---

## Table of Contents

- [Delivery Status](#delivery-status)
- [Introduction](#introduction)
- [Problem Statement](#problem-statement)
- [Proposed Solution](#proposed-solution)
- [Project Objectives](#project-objectives)
- [Target Users](#target-users)
- [Supported Application Types](#supported-application-types)
- [Multi-Agent Architecture](#multi-agent-architecture)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Development Roadmap](#development-roadmap)
- [Team Members and Responsibilities](#team-members-and-responsibilities)
- [Getting Started](#getting-started)
- [GitHub Collaboration Guidelines](#github-collaboration-guidelines)
- [Evaluation Criteria](#evaluation-criteria)
- [Security and Limitations](#security-and-limitations)
- [Future Enhancements](#future-enhancements)
- [Additional Documentation](#additional-documentation)

---

## Delivery Status

| Area | State |
|---|---|
| Five agents + orchestrator | Implemented: Business Analyst → user approval → Architect → Developer → QA (real Playwright, Chromium) → Project Manager → preview and ZIP. |
| Business Analyst | Two modes. `mock`: deterministic, recognises only the predefined example ideas (task manager, inventory, appointments/bookings…). `llm`: Claude (`claude-opus-5-5`) through the Anthropic SDK, verified with real paid runs (see [docs/SUBMISSION.md](docs/SUBMISSION.md#real-llm-evidence)). The public demo runs `mock`. |
| Architect, Developer, QA, Project Manager | Deterministic (no LLM): rules, a fixed CRUD template and a fixed 8-check Playwright suite. The PM runs in `mode="rules"`. |
| Automatic repair loop (QA → Developer) | **Deterministic, at most 2 repairs** (`BUNYAN_REPAIR=restore`): the Developer restores generated files that differ from the approved contracts and QA re-tests in real Chromium; a repair that changes nothing is not re-tested or claimed. No LLM repair. History in `repair_history.json`. (Merged after the live deployment; live shows "not available".) |
| Protected real Business Analyst | `BUNYAN_LLM_ACCESS=codes`: guests stay on mock; an access code unlocks Claude for one session, with per-code, site-wide and USD-budget limits. Off by default and not enabled on the live site. |
| Platform | React (Vite) with the Riyadh theme (light/dark, RTL/LTR, desktop/mobile), FastAPI backend. |
| Deployment | One Docker image; live on Railway in guest mode with signed sessions, per-owner isolation, quotas and a sandboxed preview. |

---

## Introduction

**BUNYAN AI** (بنيان — "structure" or "building") is a multi-agent AI platform that turns a natural-language description of a web application into a working **CRUD** (Create, Read, Update, Delete) web application.

A user describes the application they want — for example, *"a simple inventory tracker for a small shop"* — and five specialized AI agents collaborate through a structured software development workflow, similar to a real software team:

1. A **Business Analyst** clarifies the idea and writes requirements.
2. A **Software Architect** designs the application structure and data schema.
3. A **Developer** generates the application source code.
4. A **QA Tester** runs automated browser tests and reports defects.
5. A **Project Manager** produces the project plan, timeline, and risk report.

The result is a previewable, downloadable web application together with its requirements, architecture, test results, and project documentation.

The project is developed over **four weeks** by a **six-member team** at Tuwaiq Club, King Saud University.

---

## Problem Statement

Building even a simple software application involves challenges that slow down individuals and small teams:

- **Requirement misunderstandings.** Ideas are often described informally. Gaps and ambiguities between what a stakeholder means and what is built are frequently discovered only after implementation has started.
- **Development complexity.** Turning an idea into working software requires knowledge of requirements analysis, design, programming, and testing — skills that are not always available within one person or a small team.
- **Documentation overhead.** Requirements, architecture notes, test reports, and project plans take significant effort to produce and are often skipped or left outdated.
- **Late discovery of software defects.** When testing happens late, defects are more expensive and disruptive to fix.
- **Limited development resources.** Startups, small organizations, and students often lack the budget or staff to build prototypes quickly, even for straightforward data-management applications.

---

## Proposed Solution

BUNYAN AI automates a structured, end-to-end software development workflow using **five specialized AI agents**, each responsible for one phase of the process. Each agent receives well-defined inputs, produces a well-defined artifact (JSON, Markdown, or source code), and passes it to the next agent.

Key characteristics of the solution:

- **Structured workflow.** Agents follow a fixed sequence that mirrors a real development lifecycle: analysis → design → implementation → testing → project management.
- **Human in the loop.** The user reviews and approves the generated requirements before any design or code is produced.
- **Shared JSON contracts.** Agents communicate through agreed-upon JSON schemas, making outputs predictable and testable.
- **Automated quality assurance.** Generated applications are tested in a real browser with Playwright; the actual results, including failures, are reported to the user and the Project Manager. Failures go back to the Developer for a deterministic repair (at most two), and QA re-tests after each real change.
- **Complete deliverables.** Alongside the code, the user receives requirements, architecture, test results, a project plan, and a risk report.
- **Focused scope.** The MVP targets CRUD web applications only, which keeps generation reliable and results verifiable.

---

## Project Objectives

By the end of the four-week MVP, the team aims to:

1. **Generate a working CRUD web application** (HTML, CSS, JavaScript with localStorage) from a natural-language description, with all four operations — Create, Read, Update, Delete — functioning in the browser.
2. **Produce structured requirements** (`requirements.json`) containing entities, attributes, functional requirements, user stories, and acceptance criteria.
3. **Produce an architecture specification** (`architecture.json`) describing screens, components, data schema, and navigation.
4. **Run automated functional tests** with Playwright against every generated application and produce an actual test report (`test_report.json`).
5. **Automatically attempt to repair failed tests**, at most two Developer–QA iterations (deterministic strategy; see below).
6. **Generate project documentation** — a project plan (`project_plan.md`) and a risk report (`risks.md`).
7. **Provide a live preview and a downloadable package** of the generated application and all artifacts.
8. **Demonstrate successful generation across several different CRUD scenarios** (for example: task manager, appointment booking, inventory tracker, order manager) during final evaluation.

---

## Target Users

- **Students and developers** who want to quickly scaffold and study a working CRUD application.
- **Entrepreneurs** who want to validate an idea with a functional prototype.
- **Startups** that need early prototypes without dedicating full development resources.
- **Small businesses** that need simple data-management tools.
- **Teams prototyping simple CRUD applications** before committing to a full implementation.

---

## Supported Application Types

The MVP focuses **exclusively on CRUD web applications** — applications whose core purpose is to create, view, edit, and delete records.

### Examples of supported applications

| Application | Example entity | Example attributes |
|---|---|---|
| Task management | Task | title, description, due date, status |
| Simple appointment booking | Appointment | client name, date, time, notes |
| Inventory tracking | Item | name, SKU, quantity, price |
| Basic order management | Order | customer, product, quantity, status |

### Technical characteristics of generated applications

- Built with **HTML, CSS, and vanilla JavaScript**.
- Data persisted in the browser using **localStorage**.
- Single-page, client-side applications that run without a server.
- Include input validation and basic navigation between screens.

### Limitations and excluded features (MVP)

The following are **out of scope** for the MVP:

- Mobile (native) applications.
- Payment processing.
- Enterprise systems (ERP, CRM, etc.).
- Complex or custom backend generation, server-side databases, or APIs in the generated apps.
- User authentication and authorization in the generated apps.
- Real-time collaboration or multi-user data sharing.
- Deployment of generated applications to hosting providers.

Because data is stored in localStorage, it is local to a single browser and is not shared across devices or users.

---

## Multi-Agent Architecture

### Workflow

```
User Idea
   │
   ▼
Business Analyst Agent ──► requirements.json
   │
   ▼
User Approval  (user reviews and approves requirements)
   │
   ▼
Software Architect Agent ──► architecture.json
   │
   ▼
Developer Agent ──► index.html, style.css, app.js
   │        ▲
   ▼        │  real defects (max 2 deterministic repairs, re-test after each real change)
QA Tester Agent ──► test_report.json   (real Chromium, 8 fixed checks)
   │
   ▼
Project Manager Agent ──► project_plan.md, risks.md
   │
   ▼
Preview & Download
```

**In short:** User Idea → Business Analyst → User Approval → Software Architect → Developer → QA Tester → Project Manager → Preview & Download

### Agents

| # | Agent | Owner | Inputs | Outputs |
|---|---|---|---|---|
| 1 | Business Analyst | Ghala Alshreef | User idea, user answers to clarification questions | `requirements.json` |
| 2 | Software Architect | Naifah | Approved `requirements.json` | `architecture.json` |
| 3 | Developer | Yara | `requirements.json`, `architecture.json`, CRUD template, QA feedback | `index.html`, `style.css`, `app.js` |
| 4 | QA Tester | Sara | Acceptance criteria, generated application | `test_report.json` |
| 5 | Project Manager | Jood | Outputs and status from all agents | `project_plan.md`, `risks.md` |

#### 1. Business Analyst Agent

- Understands the user's application idea.
- Asks clarification questions when the idea is ambiguous.
- Identifies entities and their attributes.
- Defines functional requirements.
- Generates user stories and acceptance criteria.
- Ensures the request stays within the CRUD scope.

#### 2. Software Architect Agent

- Receives the approved requirements.
- Defines the application structure.
- Identifies required screens and components.
- Defines the data schema.
- Designs basic application behavior and navigation.
- Ensures compatibility with the CRUD application template.

#### 3. Developer Agent

- Receives the requirements and architecture.
- Generates functional HTML, CSS, and JavaScript.
- Implements Create, Read, Update, and Delete operations.
- Implements input validation.
- Implements localStorage persistence.
- Repairs the app after a QA failure by restoring every generated file that differs from the approved contracts (deterministic; see below).

#### 4. QA Tester Agent

- Generates tests from the approved acceptance criteria.
- Executes automated browser tests using Playwright.
- Verifies all four CRUD operations.
- Identifies functional defects.
- Produces actual test results and failure reports.
- Records each failed check with its real error message for the Project Manager and the user.

#### 5. Project Manager Agent

- Tracks the application generation workflow.
- Collects outputs from the other agents.
- Generates a project plan and a basic timeline.
- Identifies risks and issues.
- Summarizes project status and deliverables.

### Error-Correction Loop (QA ↔ Developer)

1. QA runs the 8 checks in Chromium (attempt 0).
2. If checks fail, the Developer gets the real defects and repairs (`restore_from_contracts`):
   it rebuilds the app the approved `requirements.json` and `architecture.json` describe and replaces
   every generated file that differs (with SHA-256 before/after in the history).
3. Only if a file changed, QA re-tests (attempt 1, then 2). At most **two** repairs.
4. The loop stops when QA passes, the repair changes nothing (no re-test, no repair claimed), the repair
   output is invalid, QA is blocked, or the budget is used. The real final report is kept, the first
   failing one is saved as `test_report.initial.json`, and `repair_history.json` lists every step.
5. Jood's Project Manager reports the attempts and files changed; the Tests view shows the history.

The strategy is deterministic and free: it repairs damaged, edited or stale generated code, not a logic
error in the template itself. An LLM-based code repair is **not implemented**. `BUNYAN_REPAIR=off`
disables the loop.

### Orchestration

The five agents are coordinated by a Python orchestrator (`backend/orchestrator/pipeline.py`) behind the **FastAPI** backend. It keeps the workflow state (`analyzing → awaiting_approval` or `awaiting_clarification` or `rejected`, then after approval `designing → developing → testing → documenting → completed`, or `failed` with an honest reason), passes the JSON contracts between agents, pauses for user approval and stores every artifact. The Business Analyst's LLM mode supports two backends: CrewAI (`BA_LLM_BACKEND=crewai`) and the Anthropic SDK directly (`BA_LLM_BACKEND=direct`), which is what the Docker image and the verified paid runs use. See [docs/architecture.md](docs/architecture.md) and [docs/SUBMISSION.md](docs/SUBMISSION.md).

---

## Technology Stack

| Layer | Technology | Role |
|---|---|---|
| Frontend | **React** | User interface for entering ideas, approving requirements, tracking progress, previewing, and downloading results. |
| Backend | **Python + FastAPI** | REST API that receives requests, runs the agent workflow, and serves artifacts. |
| Orchestration | **Python pipeline** (CrewAI optional for the BA) | Runs the five agents in order and records the state. |
| Language model | **Claude `claude-opus-5-5`** (Anthropic API) | Used by the Business Analyst in `llm` mode only. The other four agents are deterministic. |
| Deployment | **Docker**, **Railway** | One image with the frontend, backend, Node.js and Chromium. |
| Generated applications | **HTML, CSS, JavaScript** | The output web applications, built from a reusable CRUD template. |
| Generated app storage | **localStorage** | Client-side persistence for generated applications — no server or database required. |
| Testing | **Playwright** | Automated browser testing of generated applications and end-to-end testing of the platform. |
| Version control | **Git + GitHub** | Source control, branching, pull requests, code review, and (later) GitHub Actions. |

### About the language models

BUNYAN AI uses **pretrained large language models accessed through provider APIs** (such as OpenAI GPT or Anthropic Claude). The project **does not** train a custom language model and **does not** require collecting a large training dataset. The team's work focuses on agent design, prompt engineering, structured output contracts, orchestration, code templating, and automated testing.

---

## Repository Structure

```
bunyan-ai/
│
├── README.md                     # Project overview (this file)
├── .gitignore                    # Files and folders excluded from Git
├── .env.example                  # Environment variable names (no real values)
│
├── frontend/                     # React user interface
│   └── README.md
│
├── backend/                      # Python + FastAPI backend
│   ├── README.md
│   ├── agents/                   # The five CrewAI agent definitions
│   │   └── README.md
│   ├── schemas/                  # Shared JSON contracts between agents
│   │   └── README.md
│   └── orchestrator/             # Workflow state and agent coordination
│       └── README.md
│
├── templates/
│   └── crud/                     # Reusable CRUD application template
│       └── README.md
│
├── tests/
│   └── e2e/                      # Playwright end-to-end tests
│       └── README.md
│
├── docs/                         # Project documentation
│   ├── architecture.md
│   ├── team-roles.md
│   ├── development-plan.md
│   └── github-workflow.md
│
└── .github/
    └── PULL_REQUEST_TEMPLATE.md  # Default pull request description
```

| Directory | Purpose | Primary owner |
|---|---|---|
| `frontend/` | React application: idea input, requirement approval, progress tracking, preview, download, project dashboard. | Jood, Naifah |
| `backend/` | FastAPI application, API endpoints, configuration. | Alanoud |
| `backend/agents/` | Definitions, prompts, and tasks for the five agents (one module per agent). | Each agent's owner |
| `backend/schemas/` | Shared JSON schemas: `requirements`, `architecture`, `test_report`, etc. | Agreed by the whole team |
| `backend/orchestrator/` | Pipeline, workflow state, agent hand-offs. | Alanoud, Ghala (integration) |
| `templates/crud/` | The reusable HTML/CSS/JS CRUD template used by the Developer Agent. | Yara |
| `tests/e2e/` | Playwright tests for generated apps and for the platform. | Sara |
| `docs/` | Architecture, roles, plan, and collaboration guides. | Ghala (coordination), all members |

---

## Development Roadmap

### Week 1: Foundation

- Repository and collaboration setup.
- Shared JSON contracts.
- Initial agent definitions.
- CRUD template prototype.
- Frontend wireframes.
- Backend skeleton.

### Week 2: Core Integration

- Agent orchestration.
- Working CRUD generation.
- Initial frontend/backend integration.
- Functional testing.

### Week 3: Testing and Improvement

- Automated QA.
- Bug-fixing loop.
- UI enhancements.
- Preview and downloadable artifacts.

### Week 4: Validation and Final Demonstration

- End-to-end tests.
- Evaluation using several CRUD scenarios.
- Performance and reliability improvements.
- Documentation.
- Final demo.

Per-member weekly deliverables are listed in [docs/development-plan.md](docs/development-plan.md).

---

## Team Members and Responsibilities

| Member | AI agent | Technical responsibilities |
|---|---|---|
| **Ghala Alshreef** | Business Analyst Agent | Requirements analysis, clarification questions, entities and attributes, user stories and acceptance criteria, CRUD scope control. Team leadership, project coordination, deliverable review. |
| **Naifah** | Software Architect Agent | Application structure, screens and components, data schema, navigation and behavior, template compatibility. UI/UX design and frontend implementation. |
| **Yara** | Developer Agent | HTML/CSS/JavaScript generation, CRUD operations, input validation, localStorage persistence, defect fixing. Reusable CRUD template and generation logic. |
| **Sara** | QA Tester Agent | Test generation from acceptance criteria, Playwright browser tests, CRUD verification, defect reports, QA feedback. Regression and end-to-end testing. |
| **Jood** | Project Manager Agent | Workflow tracking, output collection, project plan, timeline, risks, status summaries. React frontend development and project dashboard. |
| **Alanoud** | Backend & Multi-Agent Integration | FastAPI backend, CrewAI orchestration, connecting the five agents, workflow state, frontend–backend integration, API endpoints, GitHub Actions, environment configuration. |

Detailed responsibilities and ownership boundaries: [docs/team-roles.md](docs/team-roles.md).

---

## Getting Started

**With Docker (recommended for reviewers):**

```bash
git clone https://github.com/lolo67fa/bunyan-ai.git && cd bunyan-ai
cp deploy.env.example deploy.env          # BUNYAN_AUTH=guest and BA_MODE=mock work without any key
# set BUNYAN_SESSION_SECRET in deploy.env to a long random value, e.g. from: openssl rand -hex 32
docker compose up --build -d              # then open http://localhost:8080
```

For plain `http://localhost` also set `BUNYAN_COOKIE_SECURE=false` in `deploy.env`. Details, security
controls and Railway: [DEPLOY.md](DEPLOY.md).

**For development (Python 3.11, Node.js 22):**

```bash
python -m venv .venv && . .venv/bin/activate
pip install fastapi uvicorn httpx pytest -r backend/agents/business_analyst/requirements-direct.txt
(cd tests/e2e && npm ci && npx playwright install chromium)   # the QA agent's browser tests
uvicorn backend.main:app --reload --port 8000                  # BA_MODE=mock by default
(cd frontend && npm ci && npm run dev)                         # http://localhost:5173
```

Tests: `pytest tests backend/agents`, `cd frontend && npm test`. The real Business Analyst needs
`BA_MODE=llm` and `ANTHROPIC_API_KEY` (never commit `.env`).

---

## GitHub Collaboration Guidelines

A beginner-friendly, step-by-step guide is available in [docs/github-workflow.md](docs/github-workflow.md). Summary:

### Feature branches

- Never commit directly to `main`.
- Each member works on her own feature branch:

  | Member | Branch |
  |---|---|
  | Ghala | `feature/ghala-analyst` |
  | Jood | `feature/jood-project-manager` |
  | Yara | `feature/yara-developer` |
  | Sara | `feature/sara-qa` |
  | Naifah | `feature/naifah-architect` |
  | Alanoud | `feature/alanoud-backend` |

- Additional short-lived branches may use `feature/<name>-<topic>`, `fix/<name>-<topic>`, or `docs/<topic>`.

### Issues

- Every task should have a GitHub Issue with a clear title, description, owner, and (if relevant) the week it belongs to.
- Reference issues in commits and pull requests (e.g., `Closes #12`).

### Commits

- Make small, focused commits.
- Use clear, descriptive messages in the imperative mood, e.g. `Add requirements.json schema` or `Fix localStorage update logic`.
- Never commit secrets, `.env` files, `node_modules/`, or virtual environments.

### Pull Requests

- Open a Pull Request into `main` when a piece of work is ready.
- Fill in the [pull request template](.github/PULL_REQUEST_TEMPLATE.md): summary, related issue, files changed, testing performed, integration dependencies.

### Code reviews

- Every PR needs at least **one approving review** from another team member before merging.
- Changes to shared files (`backend/schemas/`, API contracts, `README.md`) should be reviewed by the affected owners.

### Merging into `main`

- Merge only after approval and after resolving all review comments and conflicts.
- The PR author merges after approval unless the team agrees otherwise.
- Delete the feature branch after merging if it is no longer needed.

### Keeping branches synchronized

- Pull the latest `main` regularly and merge it into your feature branch to reduce conflicts:

  ```bash
  git checkout main
  git pull origin main
  git checkout feature/<your-branch>
  git merge main
  ```

### Ownership rules

- Each member implements her own assigned components.
- Avoid modifying files owned by another team member without coordinating first.
- **Shared API contracts and JSON schemas must be agreed upon before implementation.**

---

## Evaluation Criteria

The platform will be evaluated against a set of CRUD scenarios (for example: task manager, appointment booking, inventory tracker, order manager).

| Criterion | What is measured |
|---|---|
| **CRUD correctness** | Whether Create, Read, Update, and Delete each work correctly in the generated application, including persistence after page reload. |
| **Code execution** | Whether the generated application loads and runs in the browser without JavaScript errors. |
| **Test pass rate** | Percentage of Playwright tests that pass, measured both before and after the repair loop. |
| **Requirement satisfaction** | Proportion of acceptance criteria in `requirements.json` that are met by the generated application. |
| **Generation duration** | Total time from approved requirements to final artifacts, and time per agent stage. |
| **Scenario coverage** | Number of distinct CRUD scenarios for which the platform successfully generates a working, tested application. |

Results will be recorded with the actual values measured during Week 4 evaluation; no target figures are assumed in advance.

---

## Security and Limitations

- **API key management.** API keys are provided through environment variables (`.env`), which is excluded from Git. Only variable names are listed in `.env.example`. Keys must never be committed, shared in issues, or exposed to the frontend.
- **Isolated execution of AI-generated code.** Generated applications are untrusted code. They are previewed in a sandboxed environment (e.g., a sandboxed iframe) and tested in isolated Playwright browser contexts, never executed with backend privileges.
- **Synthetic test data.** Testing uses synthetic data only; no real personal or business data is used.
- **Limited automatic repair.** At most two deterministic repairs; nothing is claimed unless files really changed and QA re-tested them.
- **Shared demo controls.** The public demo uses signed anonymous guest sessions, per-owner project isolation, Origin checks, per-guest/per-address/site-wide quotas, a sandboxed preview (CSP `sandbox`) and no paid LLM access. See [DEPLOY.md](DEPLOY.md).
- **LLM output variability.** Language-model output is non-deterministic; results may vary between runs, and generated code should be reviewed before any reuse.
- **Not for production.** BUNYAN AI is an academic prototype. Neither the platform nor the generated applications are intended for production deployment.

---

## Future Enhancements

> The following items are **future work** and are **not** part of the MVP requirements.

- Support for additional web application types beyond CRUD.
- Database-backed generated applications (server-side persistence).
- Authentication and user accounts in generated applications.
- Deployment integrations for publishing generated applications.
- More advanced automated testing (e.g., accessibility, visual regression, performance testing).

---

## Additional Documentation

- [Submission package](docs/SUBMISSION.md)
- [Arabic user guide](docs/user-guide-ar.md)
- [Deployment and security](DEPLOY.md)
- [System Architecture](docs/architecture.md)
- [Team Roles and Ownership](docs/team-roles.md)
- [Four-Week Development Plan](docs/development-plan.md)
- [GitHub Workflow Guide](docs/github-workflow.md)
- [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md)

---

*BUNYAN AI — Tuwaiq Club, King Saud University.*
