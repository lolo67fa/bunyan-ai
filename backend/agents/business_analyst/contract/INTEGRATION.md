# Integration Guide: Business Analyst Agent → Architect & Orchestrator

**For:** Naifah (Software Architect Agent) · Alanoud (orchestrator / FastAPI)
**From:** Ghala (Business Analyst Agent) · **Contract:** `0.1.0-proposal` (see [`CONTRACT.md`](CONTRACT.md); **not yet approved**)

This guide covers how to call the agent and what you get back. Field-level rules and guarantees are in `CONTRACT.md`.

---

## 1. Interface at a glance

```
             AnalystInput (JSON)                       RequirementsDocument (JSON)
  idea ─┐                                     ┌─► status: ready_for_review ──► user approval ──► Architect
answers ┼─► analyze(...) [mock | llm] ────────┼─► status: needs_clarification ──► ask user ──► analyze(idea, answers)
feedback┘    parse → Pydantic → scope guard   └─► status: rejected_out_of_scope ──► show reasons, stop
```

| | Python | CLI |
|---|---|---|
| Import | `from backend.agents.business_analyst import analyze, analyze_input, AnalystInput, RequirementsDocument, AnalysisError` | `python -m backend.agents.business_analyst` |
| Call | `doc = analyze(idea, answers=None, feedback=None, mode=None)` | `--idea "..."` or `--input file.json`, `--answers a.json`, `--feedback "..."`, `--mode mock\|llm`, `--out requirements.json` |
| Returns | `RequirementsDocument` (Pydantic). Serialise with `doc.model_dump_json(indent=2)` or `doc.model_dump(mode="json")` | JSON on stdout or in `--out`; summary on stderr |
| Validate a file | `RequirementsDocument.model_validate_json(text)` or `validate_requirements_file(text)` (also runs the scope guard) | `--validate requirements.json` |
| JSON Schema (non-Python) | `json_schema()` | `--schema`; committed copy: [`requirements.schema.proposal.json`](requirements.schema.proposal.json) |
| Input from JSON | `analyze_input(AnalystInput.model_validate(payload))`. Canonical key `idea`; `prompt` accepted as a deprecated alias ([`CONTRACT.md`](CONTRACT.md) §1) | `--input file.json` |
| Errors | `AnalysisError` (no valid output after retries; `.errors`, `.raw_output`), `ConfigError` (missing model/key), `pydantic.ValidationError` (bad input: missing, blank, wordless or over-long idea, bad answers), provider SDK errors (network, auth) | exit `1` analysis/LLM failed, `2` configuration/usage error |

`mode=None` reads `BA_MODE` (default `mock`). The orchestrator should pass `mode` explicitly or set `BA_MODE=llm` in the backend environment.

## 2. For Alanoud (orchestrator / API)

### 2.1 What the backend does today (reviewed 2026-11-01, `main` at `c0b87e8`)

| Question | Today | Evidence |
|---|---|---|
| How does the frontend submit an idea? | `POST /projects` with `{"idea": "..."}` | `frontend/src/api/httpClient.js:38-39` |
| Which endpoint receives it? | `POST /projects` | `backend/main.py` |
| `idea` or `prompt`? | The backend requires **`prompt`** (`ProjectRequest`), so the frontend request is refused with **HTTP 422** | `backend/schemas/contracts.py:5` (commit `4260ceb`); reproduced with FastAPI `TestClient` |
| How does the backend call the BA? | **It does not.** `POST /projects` returns a fixed document (`project_id: "bunyan-demo-01"`, `status: "requirements_pending"`) | `backend/main.py` (commit `fbbc9b3`) |
| How are status and results exposed? | `GET /projects/{id}` returns a fixed `"completed"` result for any id | `backend/main.py` |
| How are answers submitted? | Not implemented (`POST /projects/{id}/answers` → 404) | — |
| How is approval recorded? | Not implemented (`POST /projects/{id}/approve` → 404) | — |
| How are errors returned? | Only FastAPI's default 422 for a bad body; no BA errors are mapped | — |

The fixed `requirements` object in `backend/main.py` (`entity`, `fields: [str]`, `operations`) and `RequirementModel` in `backend/schemas/contracts.py` do **not** match `requirements.json`. The BA work changed nothing in the backend; the proposals below are for Alanoud's review.

### 2.2 Keep BA status and workflow status apart

`requirements.json` → `status` is the analyst's verdict on the idea. The project's workflow state belongs to the orchestrator. Store the document as an artifact and derive the workflow state from it; do not copy one into the other:

| BA result | Suggested workflow state | Frontend shows |
|---|---|---|
| `needs_clarification` | `awaiting_clarification` | `clarification_questions` (blocking ones required) |
| `ready_for_review` | `awaiting_approval` | the document + optional questions with their `suggested_default` |
| `rejected_out_of_scope` | `failed` with `error.code = "out_of_scope"` (or a dedicated state, F2) | `out_of_scope` reasons |
| `AnalysisError` raised | `failed` with `error.code = "analysis_failed"` | `error.message` |
| `pydantic.ValidationError` on input | reject the request with HTTP 422 | FastAPI's `detail` |

### 2.3 Proposed backend patch (for Alanoud's review; not applied)

The smallest change that lets the frontend reach the BA. It renames one field and keeps the old name working during the transition:

```diff
--- a/backend/schemas/contracts.py
+++ b/backend/schemas/contracts.py
-from pydantic import BaseModel
+from pydantic import AliasChoices, BaseModel, Field
 from typing import List, Dict, Any, Optional

 class ProjectRequest(BaseModel):
-    prompt: str
+    # Canonical name shared with the frontend and the Business Analyst ("idea");
+    # "prompt" is still accepted while clients move over.
+    idea: str = Field(min_length=3, max_length=4000, validation_alias=AliasChoices("idea", "prompt"))
```

When the endpoint starts calling the agent (in a background task for LLM mode):

```python
from backend.agents.business_analyst import AnalysisError, AnalystInput, analyze_input

request = AnalystInput(idea=data.idea)                    # same validation as the agent
doc = analyze_input(request, mode=settings.ba_mode)       # "mock" until an API key is configured
project.requirements = doc.model_dump(mode="json")        # artifact: requirements.json
project.status = WORKFLOW_FOR_BA_STATUS[doc.status]       # table in 2.2
```

`RequirementModel` can then be replaced by re-exporting `RequirementsDocument` from this package once the contract is approved (D2).

### 2.4 Calling sequence

**Calling sequence (maps to the proposed workflow states in `docs/architecture.md`).** This is a sketch: `fail`, `ask`, `reject` and `await_approval` stand for your orchestrator's own functions.

```python
from backend.agents.business_analyst import analyze, AnalysisError

def run_analysis(project):                          # state: analyzing
    try:
        doc = analyze(project.idea, answers=project.answers, feedback=project.feedback, mode="llm")
    except AnalysisError as exc:                    # model never produced a valid document
        return fail(project, reasons=exc.errors)    # state: failed
    project.requirements = doc.model_dump(mode="json")
    if doc.status == "needs_clarification":         # state: awaiting_clarification
        return ask(project, [q for q in doc.clarification_questions if q.blocking])
    if doc.status == "rejected_out_of_scope":       # state: failed (or a dedicated "rejected")
        return reject(project, doc.out_of_scope)
    return await_approval(project)                  # state: awaiting_approval
```

- **Answers:** `POST /projects/{id}/answers` → store `{"Q-1": "...", "Q-2": "..."}` → call `analyze` again with the **same idea** plus `answers`. Question IDs are only stable within one document, so send the answers together with the document they belong to.
- **Approval feedback:** if the user asks for changes, call `analyze(idea, answers=..., feedback="...")` (LLM mode only; mock mode ignores feedback).
- **Approval** is orchestrator state; it is not stored in `requirements.json` (open decision D1 below).
- **Optional questions** (`blocking: false`) carry a `suggested_default` that is already applied. Show them on the approval screen; they don't need to block.
- **Artifact:** save `doc.model_dump_json(indent=2)` as `requirements.json`.
- **Timing / cost:** mock is instant. LLM mode is one model call per attempt, at most `1 + BA_MAX_RETRIES` (default 3) attempts. Run it in a background task, not in the request thread.
- **Configuration** (backend `.env`, never the frontend):

  | Variable | Default | Purpose |
  |---|---|---|
  | `BA_MODE` | `mock` | `mock` or `llm` |
  | `LLM_PROVIDER` / `LLM_MODEL` | none | project-wide model (from root `.env.example`) |
  | `BA_LLM_PROVIDER` / `BA_LLM_MODEL` | none | per-agent override |
  | `BA_LLM_BACKEND` | `crewai` | `crewai` (CrewAI agent) or `direct` (Anthropic SDK; no CrewAI install needed) |
  | `BA_EFFORT` | `high` | Anthropic `output_config.effort` (direct backend) |
  | `BA_MAX_RETRIES` | `2` | extra attempts when output fails validation |
  | `BA_FALLBACKS` | `on` | direct backend: server-side refusal fallback (`off` = a refusal is returned instead of a second, billed attempt) |
  | `BA_SDK_MAX_RETRIES` | unset (SDK default 2) | direct backend: Anthropic SDK transport retries on 429/5xx/connection errors |
  | `BA_TEMPERATURE` | unset | only forwarded to non-Anthropic providers; the Anthropic API rejects sampling parameters |
  | `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` / `OPENAI_API_KEY` | none | credentials (git-ignored `.env` only) |

- **Inside a larger CrewAI crew:** `crew.build_agent(settings)` and `crew.build_task(prompts.build_task_description(...), agent)` return the CrewAI objects. If you run the Task yourself, pass its raw output through `analyst.finalize(raw, idea, language, answers)` so validation and the scope guard still apply. **Do not skip `finalize`.**
- **Dependencies:** `backend/agents/business_analyst/requirements.txt` (mock) and `requirements-llm.txt` (+ CrewAI). Merge them into the backend's dependency file when you create it.

## 3. For Naifah (Software Architect Agent)

**Run only when** `status == "ready_for_review"` **and** the orchestrator has recorded user approval.

**Sample inputs to develop against** (all validated by the tests):

| File | Language | Entities | Shows |
|---|---|---|---|
| [`task_manager_en.requirements.json`](../samples/outputs/task_manager_en.requirements.json) | en | Task | enums with defaults, date rule, search/filter/sort |
| [`inventory_dialect_ar.requirements.json`](../samples/outputs/inventory_dialect_ar.requirements.json) | ar (Gulf dialect input) | Product | **RTL**, numeric ranges (changed 2026-11-01, see below) |
| [`inventory_manager_ar.requirements.json`](../samples/outputs/inventory_manager_ar.requirements.json) | ar | Category, Item | `reference` field, `unique`, `pattern`, an excluded out-of-scope login request |
| [`appointment_booking_en.requirements.json`](../samples/outputs/appointment_booking_en.requirements.json) | en | Appointment | `phone`, `time`, double-booking rule, out-of-scope SMS replaced by a CRUD alternative |
| [`scenario_a_task_en.requirements.json`](../samples/outputs/scenario_a_task_en.requirements.json) | en | Task | evaluation scenario A |
| [`scenario_b_inventory_ar.requirements.json`](../samples/outputs/scenario_b_inventory_ar.requirements.json) | ar (Gulf dialect) | Product | evaluation scenario B: non-negative quantity and price |
| [`scenario_c_booking_ar.requirements.json`](../samples/outputs/scenario_c_booking_ar.requirements.json) | ar (Gulf dialect) | Booking | evaluation scenario C: cancel as a status update, open business rules as optional questions |

**Change on 2026-11-01:** the Gulf-dialect inventory idea never mentions categories, so the mock no longer invents a `Category` entity for it and returns one `Product` entity instead. Ideas that ask for categories (`inventory_manager_ar`) still get `Category` + `Item`. **If you copy the new sample into `backend/agents/architect/tests/fixtures/`, point `test_multi_entity_with_reference_is_refused_with_reasons` at `inventory_manager_ar`**, because the dialect sample is no longer multi-entity. Jood: `npm run sync-samples` refreshes the frontend copies.

These were produced in **mock mode** (templates), so they are structurally identical to LLM output but not real analyses.

**What to read and what it means for the architecture:**

| requirements.json | Use in architecture.json (suggested) |
|---|---|
| `entities[].name` (PascalCase, English) | entity/schema name; localStorage key such as `bunyan.<name lowercase>` (your decision) |
| `fields[].name` (snake_case, English) | data keys. **Add** `id`, `created_at`, `updated_at` yourself |
| `fields[].label`, `entities[].label/plural_label` | UI text (already in the user's language) |
| `language == "ar"` | `dir="rtl"`, Arabic UI strings |
| `fields[].type` | input control: string→`text`, text→`textarea`, integer/decimal→`number` (decimal `step=0.01`), boolean→`checkbox`, date→`date`, time→`time`, datetime→`datetime-local`, email→`email`, phone→`tel`, url→`url`, enum→`select` of `enum_values`, reference→`select` of the target entity's records labelled by its `display_field` |
| `fields[].validation` | `minlength`/`maxlength`/`min`/`max`/`pattern`; `date_constraint: not_in_past` → `min=today`; `unique` → check before save |
| `fields[].required`, `default` | `required` attribute; initial form value |
| `crud.read.list_fields/search_fields/filter_fields/sort_field/sort_direction` | list screen columns, search box, filter controls, default sort |
| `crud.delete.requires_confirmation` | confirmation dialog |
| `display_field` | record title in lists, confirmations and reference dropdowns |
| `functional_requirements` with `category: validation` | cross-field / business rules (e.g. no double booking, "Low stock" badge) |
| `acceptance_criteria` | UI texts and behaviour QA will test: exact button labels ("Save", "Delete"), visible messages, empty state |

`tests/test_architect_handoff.py` contains a small **reference consumer** that derives all of the above from each sample, so you can see it works. It is not your agent; build yours however you like.

### 3.1 Handoff verified against the real Architect (2026-11-01)

`build_architecture()` from PR #4 (commit `6cd446a`) was run unmodified, in a separate checkout, on every sample output of this branch:

| Sample | Result |
|---|---|
| `task_manager_en`, `appointment_booking_en`, `inventory_dialect_ar`, `scenario_a_task_en`, `scenario_b_inventory_ar` | ✅ valid `architecture.json`, 0 warnings |
| `scenario_c_booking_ar` | ✅ valid, 1 warning: enum labels generated from the Arabic enum values (Naifah's request §7.2, open) |
| `inventory_manager_ar` | ❌ refused: two entities and a `reference` field (open decision D9) |
| `vague_idea_en`, `out_of_scope_ar` | ❌ refused as expected (status is not `ready_for_review`) |

`tests/test_architect_handoff.py` mirrors the Architect's input checks, so a BA change that would break them fails here too. No BA-side adapter can fix the remaining case without dropping data the user asked for, so it waits for D9.

## 4. Unresolved decisions (need the team)

Nothing below is approved. "Proposal" means a suggestion, not an agreement.

| # | Decision | Current proposal | Who |
|---|---|---|---|
| D1 | Store approval inside `requirements.json` or only in workflow state? | Workflow state only | Alanoud, Ghala |
| D2 | Approve this contract and move it to `backend/schemas/`? | Yes, after review; bump to `0.1.0` (drop `-proposal`) | Ghala, Naifah, Sara, Alanoud |
| D3 | Who adds system fields `id`, `created_at`, `updated_at`? | Architect/Developer (BA never lists them) | Naifah, Yara |
| D4 | Flat `acceptance_criteria` list (linked by `story_id`) vs nested in stories | Flat | Sara |
| D5 | localStorage key naming | PR #4 proposes `bunyan_<entity snake_case>` (one key, a JSON array); the frontend mock and older BA docs used `bunyan.<entity>`. One name is needed | Naifah, Yara |
| D6 | Delete behaviour for referenced records (e.g. Category used by Items) | BA records it as an optional question; Architect picks block vs cascade (default: block) | Naifah |
| D7 | Default model and backend for the demo | `BA_LLM_BACKEND=crewai` with `claude-opus-5-5`; `direct` as a fallback if CrewAI is not installed | Alanoud, Ghala |
| D8 | How the API exposes `needs_clarification` / `rejected_out_of_scope` to the frontend | Return the full document; the frontend shows `clarification_questions` / `out_of_scope`; mapping in §2.2 | Alanoud, Jood |
| D9 | **Single entity or several in v0.1?** | The BA contract allows several (+ `reference`); the Architect accepts one. The mock now adds a second entity only when the user asks for it. Options: (a) v0.1 = one entity, and the BA asks a question when related records are requested; (b) the Architect and the template support references | Ghala, Naifah, Yara, Sara |
| D10 | Canonical API field for the idea | `idea` (the frontend and the BA already use it); backend patch in §2.3 | Alanoud, Jood, Ghala |
| D11 | Enum identifiers and labels (Naifah's §7.2) | Not changed yet: enum values follow the user's language | Ghala, Naifah |
| D12 | Category of business rules (Naifah's §7.3: `other` instead of `validation`) | Not changed yet | Ghala, Naifah, Sara |
| D13 | Who generates `id` and timestamps at runtime | The generated app (PR #4 lists them in `entity.storage.system_fields`) | Naifah, Yara |

## 5. Verification status (be precise when reporting)

Checked 2026-10-26 on Python 3.10, CrewAI 1.15.23, anthropic 0.73.0 (venv) and 1.8.0 (system); updated 2026-11-01.

| Check | Status |
|---|---|
| Contract, validation, scope guard, CLI, input contract, status transitions, scenarios A–C, mock outputs | ✅ offline tests pass in the venv (CrewAI installed) and in system Python (CrewAI wiring test skipped there); counts in the PR description |
| Handoff to the real Architect builder (PR #4) | ✅ 6 of 7 ready samples accepted; 1 refused pending D9 (§3.1) |
| Backend can call the agent | ❌ not wired yet; frontend → backend fails with 422 (`idea` vs `prompt`), see §2.1 |
| LLM retry loop, prompt building, direct-backend request shape, refusal/truncation handling | ✅ tested with **fake** models only |
| CrewAI import, Agent/Task/Crew construction from `crew.py` | ✅ verified, now also an automated offline test (`tests/test_crew_wiring.py`, no `kickoff`) |
| Both backends reach the Anthropic API from the CLI | ✅ verified with a deliberately invalid key: request accepted by the SDK and rejected by the server with HTTP 401, clean CLI error, exit code 1 |
| **Authenticated real model call / quality of real output** | ⏳ **not yet run.** Needs an API key: follow README → LLM mode, then `BA_RUN_LLM_EVALS=1 pytest backend/agents/business_analyst/evals -v` |
