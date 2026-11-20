# Risks: Appointment Booking

| # | Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R-1 | Check “Persist after refresh” still fails | High | High | Both repair attempts are used: deliver the code with the defect report and fix it by hand. | Open |
| R-2 | Data is lost if the browser data is cleared | Medium | High | A note inside the app that data stays in this browser only; manual export is proposed for a later version. | Open |
| R-3 | Need to use the app from more than one device or user | Medium | Medium | Outside this version's scope, and stated in the requirements. | Open |
| R-4 | Architect warning: AC-8 quotes the message “This time slot is already booked” but it is not tied to one field rule (likely a business rule such as no double booking); the MVP template cannot show it | Medium | Medium | Check this behaviour by hand in the preview, or add it in a later version. | Open |
| R-5 | Requested feature left out: Messaging or third-party integration ('SMS') | Low | Medium | Show reminders inside the app (e.g. highlight records due today). | Open |
| R-6 | Run took 141 s, above the 90 s target | Medium | Low | Look at the longest stage in the timeline. | Open |
| R-7 | Requirements rest on 4 assumptions | Medium | Low | Review the assumptions with the user before a new version. | Open |

### Where each risk comes from

- R-1: `test_report.checks.persist_after_refresh`
- R-2: `architecture.entity.storage.engine`
- R-3: `project scope (single user, no server)`
- R-4: `architecture.warnings[0]`
- R-5: `requirements.out_of_scope`
- R-6: `run_time_seconds`
- R-7: `requirements.assumptions`
