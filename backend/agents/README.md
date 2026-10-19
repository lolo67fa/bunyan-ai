# Agents

Definitions of the five BUNYAN AI agents (role, goal, prompt, task, and expected output). Each agent is implemented in its own module by its owner.

| Agent | Owner | Output |
|---|---|---|
| Business Analyst | Ghala Alshreef | `requirements.json` |
| Software Architect | Naifah | `architecture.json` |
| Developer | Yara | `index.html`, `style.css`, `app.js` |
| QA Tester | Sara | `test_report.json` |
| Project Manager | Jood | `project_plan.md`, `risks.md` |

Agent outputs must conform to the schemas in [`../schemas/`](../schemas/). Integration into the workflow is handled in [`../orchestrator/`](../orchestrator/) by Alanoud.

## Status

Not yet implemented.
