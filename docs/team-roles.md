# Team Roles and Ownership

This document defines the responsibilities and ownership boundaries for each of the six BUNYAN AI team members.

## Ownership Principles

- Each member implements her own assigned components.
- Avoid modifying files owned by another member without coordinating with her first (via the related Issue, PR comment, or team chat).
- **Shared contracts** — JSON schemas in `backend/schemas/` and API request/response formats — must be agreed upon by the affected members **before** implementation, and changes to them require review by every affected owner.
- The repository-level files (`README.md`, `docs/`, `.github/`) are coordinated by the team lead; any member may propose changes through a PR.

## Summary

| Member | AI agent / role | Primary areas | Feature branch |
|---|---|---|---|
| Ghala Alshreef | Business Analyst Agent · Team Lead | `backend/agents/` (analyst), `requirements` schema, `docs/` | `feature/ghala-analyst` |
| Naifah | Software Architect Agent | `backend/agents/` (architect), `architecture` schema, frontend UI/UX | `feature/naifah-architect` |
| Yara | Developer Agent | `backend/agents/` (developer), `templates/crud/` | `feature/yara-developer` |
| Sara | QA Tester Agent | `backend/agents/` (QA), `test_report` schema, `tests/e2e/` | `feature/sara-qa` |
| Jood | Project Manager Agent | `backend/agents/` (project manager), `frontend/` (React, dashboard) | `feature/jood-project-manager` |
| Alanoud | Backend & Multi-Agent Integration | `backend/` (FastAPI), `backend/orchestrator/`, `.github/workflows/`, `.env.example` | `feature/alanoud-backend` |

---

## Ghala Alshreef — Business Analyst Agent & Team Lead

**Agent responsibilities**
- Understand the user's application idea.
- Ask clarification questions when necessary.
- Identify entities and their attributes.
- Define functional requirements.
- Generate user stories and acceptance criteria.
- Ensure the project stays within the CRUD scope.

**Expected output:** `requirements.json`

**Additional responsibilities**
- Team leadership and project coordination.
- Reviewing deliverables.
- Maintaining project scope.
- Coordinating shared documentation (`README.md`, `docs/`).

**Owns:** Business Analyst agent module, the `requirements.json` schema (in agreement with Naifah and Sara), project documentation.

**Coordinates with:** Naifah (requirements → architecture), Sara (acceptance criteria → tests), Alanoud (agent integration).

---

## Naifah — Software Architect Agent

**Agent responsibilities**
- Receive approved requirements.
- Define application structure.
- Identify required screens and components.
- Define the data schema.
- Design basic application behavior and navigation.
- Ensure compatibility with the CRUD application template.

**Expected output:** `architecture.json`

**Additional responsibilities**
- UI/UX design for the platform.
- Frontend implementation (in coordination with Jood).

**Owns:** Software Architect agent module, the `architecture.json` schema (in agreement with Ghala and Yara), UI/UX designs and assigned frontend screens.

**Coordinates with:** Ghala (input), Yara (template compatibility), Jood (frontend).

---

## Yara — Developer Agent

**Agent responsibilities**
- Receive application requirements and architecture.
- Generate functional HTML, CSS, and JavaScript.
- Implement Create, Read, Update, and Delete operations.
- Implement input validation.
- Implement localStorage persistence.
- Fix defects based on QA feedback.

**Expected outputs:** `index.html`, `style.css`, `app.js`

**Additional responsibilities**
- The reusable CRUD code template.
- Code generation logic.

**Owns:** Developer agent module, `templates/crud/`.

**Coordinates with:** Naifah (architecture format), Sara (failure report format and repair loop), Alanoud (integration).

---

## Sara — QA Tester Agent

**Agent responsibilities**
- Generate tests from approved acceptance criteria.
- Execute automated browser tests using Playwright.
- Verify all four CRUD operations.
- Identify functional defects.
- Produce actual test results and failure reports.
- Send relevant feedback to the Developer Agent.

**Expected output:** `test_report.json`

**Additional responsibilities**
- Regression testing.
- End-to-end testing of the platform.

**Owns:** QA Tester agent module, the `test_report.json` schema, `tests/e2e/`.

**Coordinates with:** Ghala (acceptance criteria format), Yara (feedback format), Alanoud (running Playwright from the backend).

---

## Jood — Project Manager Agent

**Agent responsibilities**
- Track the application generation workflow.
- Collect outputs from the other agents.
- Generate a project plan.
- Generate a basic timeline.
- Identify risks and issues.
- Summarize project status and deliverables.

**Expected outputs:** `project_plan.md`, `risks.md`

**Additional responsibilities**
- React frontend development.
- Project dashboard (progress, artifacts, preview, download).

**Owns:** Project Manager agent module, `frontend/` (shared with Naifah for assigned screens).

**Coordinates with:** Alanoud (API contracts and workflow state), Naifah (UI/UX).

---

## Alanoud — Backend and Multi-Agent Integration

Alanoud does not own a sixth AI agent; she connects the five agents into one working system.

**Responsibilities**
- FastAPI backend development.
- Multi-agent orchestration using CrewAI.
- Connecting the five agents.
- Maintaining the workflow state.
- Integrating frontend and backend.
- API endpoints.
- GitHub Actions and environment configuration.

**Owns:** `backend/` application code (outside individual agent modules), `backend/orchestrator/`, `.github/workflows/` (when added), `.env.example`, backend dependency configuration.

**Coordinates with:** Every agent owner (agent interfaces), Jood and Naifah (API contracts for the frontend), Sara (test execution).

---

## Shared Ownership

| Item | Agreed by |
|---|---|
| `requirements.json` schema | Ghala, Naifah, Sara, Alanoud |
| `architecture.json` schema | Naifah, Yara, Alanoud |
| `test_report.json` schema and QA→Developer feedback format | Sara, Yara, Jood, Alanoud |
| Backend ↔ frontend API contract | Alanoud, Jood, Naifah |
| `README.md` and `docs/` | Ghala (coordination), all members |
