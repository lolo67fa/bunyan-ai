# Backend

Python + FastAPI backend that exposes the BUNYAN AI API and runs the multi-agent workflow.

**Owner:** Alanoud (backend and multi-agent integration)

| Folder | Purpose |
|---|---|
| [`agents/`](agents/) | The five CrewAI agent definitions. |
| [`schemas/`](schemas/) | Shared JSON contracts between agents and with the frontend. |
| [`orchestrator/`](orchestrator/) | Workflow sequencing, state, and the QA–Developer repair loop. |

## Status

Not yet implemented. Dependencies, configuration, and run instructions will be added here as the backend skeleton is built.

Configuration is read from environment variables — see [`../.env.example`](../.env.example). See [`../docs/architecture.md`](../docs/architecture.md) for the proposed API.
