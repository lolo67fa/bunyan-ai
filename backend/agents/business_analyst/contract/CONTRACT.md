# Business Analyst Agent — Input / Output Contract

> **PROPOSAL `0.1.0-proposal` — not yet approved by the team.**
> The shared `requirements` schema in [`backend/schemas/`](../../../schemas/) has not been agreed yet. This file is the **provisional** contract between the Business Analyst Agent and its consumers, so the work can continue in parallel. When Ghala, Naifah, Sara and Alanoud have reviewed it, it can be moved to `backend/schemas/` as the approved shared schema. Until then, `backend/schemas/` is unchanged.

| | |
|---|---|
| Producer | Business Analyst Agent (`backend/agents/business_analyst/`), Ghala |
| Consumers | Software Architect Agent (Naifah), QA Tester Agent (Sara: acceptance criteria), Developer Agent (Yara: fields and validation), orchestrator (Alanoud: status and questions) |
| Source of truth | [`schema.py`](../schema.py) (Pydantic v2) |
| Machine-readable copy | [`requirements.schema.proposal.json`](requirements.schema.proposal.json) (JSON Schema 2020-12, generated, do not edit by hand) |
| Example outputs | [`../samples/outputs/`](../samples/outputs/) |

---

## 1. Input: `AnalystInput`

```json
{
  "idea": "I need a simple task manager for my studies ...",
  "answers": { "Q-1": "Tasks for my studies", "Q-2": "Title, due date, priority and status" },
  "feedback": null
}
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `idea` | string (min 3 chars) | yes | The application idea, in **Arabic or English**. |
| `answers` | object string → string | no | Answers to earlier clarification questions, keyed by question id (`Q-1`) or question text. Send them with the **same** `idea` to get a revised document. |
| `feedback` | string | no | Change requests from the user approval step (LLM mode only). |
| `title` | string | no | Label for sample files; ignored by the agent. |

Python API: `analyze(idea, answers=None, feedback=None, mode=None) -> RequirementsDocument`.

## 2. Output: `requirements.json` (`RequirementsDocument`)

Top level:

| Field | Type | Notes |
|---|---|---|
| `schema_version` | `"0.1.0-proposal"` | Constant. Consumers should check it. |
| `status` | `ready_for_review` \| `needs_clarification` \| `rejected_out_of_scope` | See §3. |
| `language` | `en` \| `ar` | Language of every human-readable string. Detected from the idea. `ar` means the UI should be right-to-left. |
| `source_idea` | string | The original idea, unchanged. |
| `app` | `{name, description, target_users[]}` | |
| `entities` | `Entity[]` | Data model. See below. |
| `functional_requirements` | `{id: "FR-n", entity, category, description, priority}[]` | `category` ∈ create, read, update, delete, validation, persistence, other. `priority` ∈ must, should, could. |
| `user_stories` | `{id: "US-n", role, goal, benefit, entity, operation, requirement_ids[]}[]` | "As a *role*, I want to *goal*, so that *benefit*". |
| `acceptance_criteria` | `{id: "AC-n", story_id, category, given, when, then}[]` | Flat list linked to stories by `story_id`. Used by QA to write Playwright tests. |
| `clarification_questions` | `{id: "Q-n", question, reason, blocking, options[], suggested_default}[]` | |
| `assumptions` | string[] | Decisions the agent made because the idea did not say. |
| `out_of_scope` | `{feature, category, reason, action, alternative}[]` | Features requested but **not** built. See §4. |

### Entity

| Field | Notes |
|---|---|
| `name` | **English PascalCase singular identifier** (`Task`, `Item`). Use it for code, storage keys and routes. |
| `label`, `plural_label` | Display names in the document language. |
| `display_field` | Field used as the record title in lists and delete confirmations. |
| `fields` | At least one `EntityField`. |
| `crud.create / update` | `{enabled, details}` |
| `crud.read` | `{enabled, details, list_fields[], search_fields[], filter_fields[], sort_field, sort_direction}`. All names refer to fields of this entity. |
| `crud.delete` | `{enabled, details, requires_confirmation}` |

### EntityField

| Field | Notes |
|---|---|
| `name` | **English snake_case identifier**. Never `id`, `created_at` or `updated_at`: **the Architect/Developer add these system fields to every entity.** |
| `label` | Form label in the document language. |
| `type` | `string` (single line), `text` (multi-line), `integer`, `decimal`, `boolean`, `date` (YYYY-MM-DD), `time` (HH:MM), `datetime`, `email`, `phone`, `url`, `enum`, `reference`. |
| `required`, `unique` | booleans |
| `enum_values` | Only for `enum` (≥ 2 distinct values, in the document language). |
| `reference_entity` | Only for `reference`; the `name` of another entity. Store the referenced record's `id`; show its `display_field`. |
| `default` | Optional default value (must be one of `enum_values` for enums). |
| `validation` | `{min_length, max_length, pattern}` for text types; `{min_value, max_value}` for `integer`/`decimal`; `{date_constraint: "not_in_past" \| "not_in_future"}` for `date`/`datetime`. `pattern` is a JavaScript-compatible regex. |

## 3. Status and what consumers should do

| `status` | Meaning | Orchestrator | Architect |
|---|---|---|---|
| `ready_for_review` | Complete and internally consistent. May contain **optional** (non-blocking) questions with a `suggested_default`. | Show to the user for approval. | Run **only after the user approves**. |
| `needs_clarification` | At least one **blocking** question. Entities may be empty or partial. | Show the questions, collect answers, call the agent again with `answers`. | Do not run. |
| `rejected_out_of_scope` | Nothing CRUD remains after removing out-of-scope features. | Show `out_of_scope` reasons and the suggested alternative question. | Do not run. |

Approval is recorded by the orchestrator, not in this document.

## 4. Guarantees (enforced by validation, so consumers can rely on them)

Every document the agent returns has passed these checks; an LLM answer that fails them is sent back to the model with the errors (up to `BA_MAX_RETRIES` times) and is never returned.

1. JSON matches the schema; unknown keys are rejected.
2. IDs are unique and well-formed; every cross-reference resolves: story→requirements, criterion→story, requirement/story→entity, reference field→entity, `display_field` / list / search / filter / sort fields→fields of the entity.
3. Field rules fit the type (no `min_value` on text, enums have values, etc.).
4. Every entity supports at least create and read.
5. When `ready_for_review`:
   - at least one entity, and at least one entity supports all four CRUD operations;
   - every enabled operation of every entity has at least one functional requirement **and** one user story;
   - every user story has at least one acceptance criterion;
   - no blocking questions remain.
6. Acceptance criteria are Given/When/Then; `then` may not contain vague words (fast, easy, user-friendly, intuitive, properly, سهل, سريع ...).
7. **CRUD scope:** no requirement, story, criterion or field describes authentication, payment processing, native mobile apps, a custom server/database, real-time multi-user features, enterprise systems, messaging/third-party integrations or file uploads. A deterministic guard also adds any such feature mentioned in the idea to `out_of_scope` if the analyst missed it.

`action: "replaced_with_crud_alternative"` means the CRUD version **is** in the requirements (for example a `payment_status` enum field instead of online payment). `action: "excluded"` means it is simply not built.

## 5. Example (shortened)

Full files: [`../samples/outputs/task_manager_en.requirements.json`](../samples/outputs/task_manager_en.requirements.json), and the Arabic [`inventory_manager_ar.requirements.json`](../samples/outputs/inventory_manager_ar.requirements.json).

```json
{
  "schema_version": "0.1.0-proposal",
  "status": "ready_for_review",
  "language": "en",
  "source_idea": "I need a simple task manager for my studies. ...",
  "app": { "name": "Task Manager", "description": "A single-user web app to ...", "target_users": ["Students", "Individual professionals"] },
  "entities": [{
    "name": "Task", "label": "Task", "plural_label": "Tasks", "display_field": "title",
    "fields": [
      { "name": "title", "label": "Title", "type": "string", "required": true, "validation": { "min_length": 3, "max_length": 100 } },
      { "name": "due_date", "label": "Due date", "type": "date", "required": false, "validation": { "date_constraint": "not_in_past" } },
      { "name": "priority", "label": "Priority", "type": "enum", "required": true, "enum_values": ["low", "medium", "high"], "default": "medium" }
    ],
    "crud": {
      "create": { "enabled": true }, "update": { "enabled": true },
      "read": { "enabled": true, "list_fields": ["title", "due_date", "priority", "status"], "search_fields": ["title"], "filter_fields": ["status", "priority"], "sort_field": "due_date", "sort_direction": "asc" },
      "delete": { "enabled": true, "requires_confirmation": true }
    }
  }],
  "functional_requirements": [{ "id": "FR-1", "entity": "Task", "category": "create", "priority": "must", "description": "The system shall allow the user to create a Task by entering: Title, Description, Due date, Priority, Status." }],
  "user_stories": [{ "id": "US-1", "role": "user", "goal": "add a new Task", "benefit": "I can keep a record of it", "entity": "Task", "operation": "create", "requirement_ids": ["FR-1", "FR-5", "FR-6"] }],
  "acceptance_criteria": [{ "id": "AC-1", "story_id": "US-1", "category": "create", "given": "the Tasks list is open with N records", "when": "the user fills in Title = \"Prepare sprint report\", Priority = \"high\", Status = \"to_do\" and clicks \"Save\"", "then": "a Task named \"Prepare sprint report\" appears in the list and the list shows N + 1 records" }],
  "clarification_questions": [{ "id": "Q-1", "question": "Do you want to group tasks into categories or projects?", "blocking": false, "suggested_default": "No categories in the first version." }],
  "assumptions": ["The app is used by one person in one browser; data is stored in localStorage."],
  "out_of_scope": []
}
```

## 6. Open points for team review

1. Should approval be stored inside `requirements.json` (e.g. `approved_at`) or only in the orchestrator's workflow state? (Current proposal: orchestrator only.)
2. Is a flat `acceptance_criteria` list linked by `story_id` convenient for QA, or does Sara prefer criteria nested inside each story?
3. Does the Architect want the agent to suggest screens, or should screens stay entirely in `architecture.json`? (Current proposal: Architect only.)
4. Are the system fields `id`, `created_at`, `updated_at` the right defaults for the CRUD template (Yara)?

## 7. Versioning

- `schema_version` changes on every contract change. While the contract is a proposal it stays `0.x.y-proposal`.
- After changing `schema.py`, run `python backend/agents/business_analyst/regenerate_samples.py`. The offline tests fail if the committed JSON Schema or sample outputs are stale.
