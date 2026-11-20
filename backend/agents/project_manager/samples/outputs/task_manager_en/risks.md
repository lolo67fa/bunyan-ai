# Risks: Task Manager

| # | Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R-1 | Data is lost if the browser data is cleared | Medium | High | A note inside the app that data stays in this browser only; manual export is proposed for a later version. | Open |
| R-2 | Need to use the app from more than one device or user | Medium | Medium | Outside this version's scope, and stated in the requirements. | Open |
| R-3 | Requirements rest on 3 assumptions | Medium | Low | Review the assumptions with the user before a new version. | Open |

### Where each risk comes from

- R-1: `architecture.entity.storage.engine`
- R-2: `project scope (single user, no server)`
- R-3: `requirements.assumptions`
