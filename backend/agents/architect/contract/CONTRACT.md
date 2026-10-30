# `architecture.json` contract — v0.2.0-proposal (NOT YET APPROVED)

**Owner:** Naifah (Software Architect Agent)
**Input:** `requirements.json` v0.1.0-proposal from Ghala (`feature/ghala-analyst`, [`INTEGRATION.md`](../../business_analyst/contract/INTEGRATION.md))
**Consumers:** Yara (Developer / CRUD template), Sara (fixed QA suite), Jood (PM agent), Alanoud (orchestrator)
**Source of truth:** [`../schema.py`](../schema.py) (Pydantic). [`architecture.schema.proposal.json`](architecture.schema.proposal.json) is generated from it; do not edit by hand.

---

## 1. Principles

1. **Names are copied, never invented.** Entity `name`, field `name`, `label`, `type`, `required`, `unique`, `default` and every `validation` rule come from requirements.json unchanged. The same names flow to the template and the tests.
2. **Structure only.** No HTML, CSS or `data-testid` in this file. The template derives testids from field names by the fixed rules in §5.
3. **Deterministic first.** [`../from_requirements.py`](../from_requirements.py) derives the whole document in code. Same input → same output. A model is only needed later for the items listed in `warnings`.
4. **MVP limits are enforced, not hoped for.** One entity, no `reference` fields, full CRUD, max 12 fields, two screens. Anything else is refused with reasons (§4).

## 2. Mapping from requirements.json

| requirements.json | architecture.json |
|---|---|
| `language` | `app.language`; `app.direction` = `rtl` for `ar`, `ltr` for `en` |
| `app.name/description` | `app.name/description` |
| `entities[0].name/label/plural_label/display_field` | `entity.*` (same values) |
| `entities[0].name` | `entity.storage.key` = `bunyan_<snake_case>` (e.g. `Appointment` → `bunyan_appointment`) |
| — | `entity.storage.system_fields` = `id`, `created_at`, `updated_at` (added by the app, **decision D3**) |
| `fields[].type` | `type` (unchanged) + `input`: string→`text`, text→`textarea`, integer/decimal→`number`, boolean→`checkbox`, date→`date`, time→`time`, datetime→`datetime-local`, email→`email`, phone→`tel`, url→`url`, enum→`select` |
| `fields[].enum_values` | `options: [{value, label}]` |
| integer / decimal | `step` = `1` / `0.01` |
| `fields[].validation` | `validation` (same keys; nulls dropped) |
| `crud.read.list_fields` | `table.columns` and `fields[].show_in_list` |
| `crud.read.search_fields` | `search` component (text fields only) |
| `crud.read.filter_fields` | `filters` component (enum / boolean / date only) |
| `crud.read.sort_field/direction` | `table.sort` |
| `crud.delete.requires_confirmation` | `behaviors.delete_confirmation` = `inline` / `none` |
| any `unique` field | `behaviors.check_unique_before_save = true` |
| `functional_requirements[]` with `category: "other"` | `deferred_rules` (not built in MVP; PM records them as risks) |

## 3. Document shape

```text
schema_version   "0.2.0-proposal"
source           { requirements_schema_version }
app              { name, description, language, direction }
entity           { name, label, plural_label, display_field, storage{...}, fields[ ≤12 ] }
screens          [ list, form ]
  list           header, add_button, search?, filters?, table{columns, sort?, row_actions}, empty_state
  form           form_fields (every field, in order), save_button, cancel_button; modes [create, edit]
navigation       initial_screen "list"; transitions add/edit → form, save_success/cancel → list
behaviors        validate_before_save, check_unique_before_save, prefill_form_on_edit, load_on_start,
                 delete_confirmation (inline | none), after_save, after_delete
messages         empty, required, invalid, unique, created, updated, deleted, confirm_delete,
                 confirm_button, cancel_delete_button, edit_button, delete_button
deferred_rules   [{ requirement_id, description }]
warnings         [ string ]
```

`messages.confirm_delete` contains `{display}`; the app replaces it with the record's `display_field` value.
Inline confirmation means an in-page confirm button, **never** `window.confirm()`, so Playwright needs no dialog handling.

## 4. When the Architect refuses

`build_architecture` raises `ArchitectureError(reasons)` (CLI exit code `1`) when:

- `status` is not `ready_for_review` (the orchestrator must also have recorded user approval);
- there is not exactly one entity;
- any field is a `reference`;
- any CRUD operation is disabled;
- the entity has more than 12 fields.

Example (Ghala's `inventory_dialect_ar` sample):

```text
- MVP supports exactly one entity, got 2: ['Category', 'Item']
- entity 'Item' has reference fields ['category']; relations are out of MVP scope
```

## 5. `data-testid` rules (to agree with Yara and Sara)

| Element | `data-testid` |
|---|---|
| Screens | `screen-list`, `screen-form` |
| Add / save / cancel | `btn-add`, `btn-save`, `btn-cancel` |
| Search box | `search-input` |
| Filter control of a field | `filter-<field>` |
| Table / one row | `records-table` / `record-row` (+ `data-id="<id>"`) |
| Cell of a field | `cell-<field>` |
| Row actions | `btn-edit`, `btn-delete` |
| Inline delete confirm / cancel | `btn-confirm-delete`, `btn-cancel-delete` |
| Empty state | `empty-state` |
| Input / error of a field | `input-<field>`, `error-<field>` |
| Success / info message | `toast` |

## 6. Ghala's open decisions that are mine

| # | Decision | Answer |
|---|---|---|
| D3 | Who adds `id`, `created_at`, `updated_at`? | The generated app, listed in `entity.storage.system_fields`. The BA never lists them; the Architect never puts them in `fields`. |
| D5 | localStorage key naming | `bunyan_<entity snake_case>`, one key holding a JSON array. |
| D6 | Deleting referenced records | Not applicable in the MVP: references are refused (§4). |

## 7. Requests to the Business Analyst contract

1. **One entity, no `reference`, in v0.1.** The plan, the template and Sara's fixed 8-check suite all assume one entity. Two inventory samples currently use two related entities.
2. **Display labels for enum values.** `enum_values` are identifiers (`to_do`, `in_progress`). For Arabic apps the UI needs Arabic labels; the Architect can only humanize English today and adds a warning. Proposal: `enum_labels: {"to_do": "قيد الانتظار", ...}` next to `enum_values`.
3. **Separate field rules from business rules.** Field-level checks are already in `fields[].validation`. Rules that are not (e.g. "no double booking", "low stock badge") are also `category: "validation"`, so the Architect cannot tell them apart. Proposal: use `category: "other"` for any rule that `fields[].validation` cannot express; the Architect moves those to `deferred_rules`.

## 8. Open questions

| # | Question | Who |
|---|---|---|
| A1 | Does the template support every `input` control in §2 (especially `datetime-local`, `checkbox`, `url`)? Remove any that are costly now. | Yara |
| A2 | Do the §5 testids cover all 8 fixed checks? Does the suite need `filter-*` / `search-input` or are they out of the 8? | Sara |
| A3 | Port this Pydantic model to `backend/schemas/` after approval, alongside `requirements`. | Alanoud |
| A4 | Should `messages` take exact wording from acceptance criteria (e.g. "Save") instead of language defaults? Today they match by convention. | Ghala, Sara |
