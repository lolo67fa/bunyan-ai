# Agents

Definitions of the five BUNYAN AI agents (role, goal, prompt, task, and expected output). Each agent is implemented in its own module by its owner.

| Agent | Owner | Output |
|---|---|---|
| Business Analyst | Ghala Alshreef | `requirements.json` |
| Software Architect | Naifah | `architecture.json` |
| Developer | Yara | `index.html`, `style.css`, `app.js` |
| QA Tester | Sara | `test_report.json` |
| Project Manager | Jood | `project_plan.md`, `risks.md` |

The agents are run in order by [`../orchestrator/`](../orchestrator/), which documents the pipeline, its states and its errors.

## Status

All five agents are implemented and connected on the integration branch. The Architect, the Developer and the Project Manager are deterministic (no LLM). The Business Analyst can use an LLM but the API currently runs it in mock mode. The QA ↔ Developer repair loop is not implemented.
