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
| Errors | `AnalysisError` (no valid output after retries; `.errors`, `.raw_output`), `ConfigError` (missing model/key), `pydantic.ValidationError` (bad input), provider SDK errors (network, auth) | exit `1` analysis/LLM failed, `2` configuration/usage error |

`mode=None` reads `BA_MODE` (default `mock`). The orchestrator should pass `mode` explicitly or set `BA_MODE=llm` in the backend environment.

## 2. For Alanoud (orchestrator / API)

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
| [`inventory_dialect_ar.requirements.json`](../samples/outputs/inventory_dialect_ar.requirements.json) | ar (Gulf dialect input) | Category, Item | **RTL**, `reference` field, `unique`, `pattern`, numeric ranges |
| [`inventory_manager_ar.requirements.json`](../samples/outputs/inventory_manager_ar.requirements.json) | ar | Category, Item | same + an excluded out-of-scope login request |
| [`appointment_booking_en.requirements.json`](../samples/outputs/appointment_booking_en.requirements.json) | en | Appointment | `phone`, `time`, double-booking rule, out-of-scope SMS replaced by a CRUD alternative |

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

## 4. Unresolved decisions (need the team)

| # | Decision | Current proposal | Who |
|---|---|---|---|
| D1 | Store approval inside `requirements.json` or only in workflow state? | Workflow state only | Alanoud, Ghala |
| D2 | Approve this contract and move it to `backend/schemas/`? | Yes, after review; bump to `0.1.0` (drop `-proposal`) | Ghala, Naifah, Sara, Alanoud |
| D3 | Who adds system fields `id`, `created_at`, `updated_at`? | Architect/Developer (BA never lists them) | Naifah, Yara |
| D4 | Flat `acceptance_criteria` list (linked by `story_id`) vs nested in stories | Flat | Sara |
| D5 | localStorage key naming | Architect decides (e.g. `bunyan.<entity>`) | Naifah, Yara |
| D6 | Delete behaviour for referenced records (e.g. Category used by Items) | BA records it as an optional question; Architect picks block vs cascade (default: block) | Naifah |
| D7 | Default model and backend for the demo | `BA_LLM_BACKEND=crewai` with `claude-opus-5-5`; `direct` as a fallback if CrewAI is not installed | Alanoud, Ghala |
| D8 | How the API exposes `needs_clarification` / `rejected_out_of_scope` to the frontend | Return the full document; the frontend shows `clarification_questions` / `out_of_scope` | Alanoud, Jood |

## 5. Verification status (be precise when reporting)

| Check | Status |
|---|---|
| Contract, validation, scope guard, CLI, mock outputs | ✅ automated offline tests (`tests/`) |
| LLM retry loop, prompt building, direct-backend request shape, refusal handling | ✅ tested with **fake** models only |
| Real model call (direct backend) | ⏳ **not yet run.** Needs an API key. Run `evals/` or the command in the README |
| CrewAI backend with a real model | ⏳ **not yet run** |
