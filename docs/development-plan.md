# Four-Week Development Plan

This plan lists weekly milestones and the expected deliverables of each team member. It will be refined in weekly team meetings; changes should be proposed through a Pull Request so the plan stays current.

## Milestones at a Glance

| Week | Theme | Milestone (end of week) |
|---|---|---|
| 1 | Foundation | Repository ready, JSON contracts agreed, agents defined, CRUD template prototype, wireframes, backend skeleton. |
| 2 | Core Integration | One idea flows through all agents and produces a working CRUD app; frontend talks to backend. |
| 3 | Testing and Improvement | Automated QA with repair loop; preview and download available in the UI. |
| 4 | Validation and Final Demonstration | Evaluated across several CRUD scenarios; documentation complete; final demo delivered. |

---

## Week 1: Foundation

**Goals:** Repository and collaboration setup · Shared JSON contracts · Initial agent definitions · CRUD template prototype · Frontend wireframes · Backend skeleton

| Member | Deliverables |
|---|---|
| **Ghala** | Repository structure and documentation; GitHub Issues for Week 1–2 tasks; draft `requirements.json` schema; initial Business Analyst agent definition (role, goal, prompt). |
| **Naifah** | Draft `architecture.json` schema; initial Software Architect agent definition; frontend wireframes and UI/UX flow. |
| **Yara** | CRUD template prototype in `templates/crud/` (HTML/CSS/JS with localStorage); initial Developer agent definition. |
| **Sara** | Draft `test_report.json` schema; initial QA Tester agent definition; Playwright proof-of-concept test against the CRUD template prototype. |
| **Jood** | Initial Project Manager agent definition; draft `project_plan.md` / `risks.md` output format; React project scaffold. |
| **Alanoud** | FastAPI backend skeleton; CrewAI setup; environment configuration (`.env.example`); proposed API contract. |

**Team checkpoint:** All JSON schemas and the API contract are reviewed and agreed before Week 2 implementation.

---

## Week 2: Core Integration

**Goals:** Agent orchestration · Working CRUD generation · Initial frontend/backend integration · Functional testing

| Member | Deliverables |
|---|---|
| **Ghala** | Business Analyst agent producing valid `requirements.json`, including clarification questions and scope check; coordination of integration. |
| **Naifah** | Architect agent producing valid `architecture.json` from approved requirements; frontend screens for idea input and requirement approval. |
| **Yara** | Developer agent generating `index.html`, `style.css`, `app.js` from requirements + architecture using the template. |
| **Sara** | QA agent generating Playwright tests from acceptance criteria; first functional tests on generated apps. |
| **Jood** | Project Manager agent producing `project_plan.md` and `risks.md`; frontend connected to backend status endpoint. |
| **Alanoud** | Orchestrator running the full sequence with the user-approval pause; core API endpoints; workflow state tracking. |

**Team checkpoint:** One sample idea (e.g., a task manager) runs end to end and produces a working CRUD app.

---

## Week 3: Testing and Improvement

**Goals:** Automated QA · Bug-fixing loop · UI enhancements · Preview and downloadable artifacts

| Member | Deliverables |
|---|---|
| **Ghala** | Improved requirement quality and acceptance criteria; review of all agent outputs against scope. |
| **Naifah** | Architecture improvements for template compatibility; UI/UX enhancements. |
| **Yara** | Developer agent repair logic using QA feedback; template improvements (validation, edge cases). |
| **Sara** | Automated QA run on every generation; structured failure reports; QA → Developer feedback. |
| **Jood** | Project dashboard: progress, artifacts, preview, download; risks include unresolved test failures. |
| **Alanoud** | Repair loop (max two attempts) in the orchestrator; sandboxed preview endpoint; ZIP download endpoint. |

**Team checkpoint:** Generation, testing, repair, preview, and download all work from the UI.

---

## Week 4: Validation and Final Demonstration

**Goals:** End-to-end tests · Evaluation using several CRUD scenarios · Performance and reliability improvements · Documentation · Final demo

| Member | Deliverables |
|---|---|
| **Ghala** | Evaluation scenario list; collection of evaluation results; final README and documentation review; demo coordination. |
| **Naifah** | Final UI polish; architecture documentation. |
| **Yara** | Reliability fixes in generation; template documentation. |
| **Sara** | End-to-end and regression test suite for the platform; evaluation test results per scenario. |
| **Jood** | Final dashboard; final project plan and risk summary for the demo. |
| **Alanoud** | Performance and reliability improvements; GitHub Actions (if adopted); final setup instructions. |

**Team checkpoint:** Final demonstration.

---

## Evaluation Scenarios (proposed)

- Task management
- Simple appointment booking
- Inventory tracking
- Basic order management

Each scenario will be measured on CRUD correctness, code execution, test pass rate, requirement satisfaction, and generation duration (see the [Evaluation Criteria](../README.md#evaluation-criteria) section of the README).
