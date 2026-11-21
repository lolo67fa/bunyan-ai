# `architecture.json` contract — v0.3.0-proposal (NOT YET APPROVED)

**Owner:** Naifah (Software Architect Agent)
**Input:** `requirements.json` v0.1.0-proposal from Ghala (`backend/agents/business_analyst`, [`INTEGRATION.md`](../../business_analyst/contract/INTEGRATION.md))
**Consumers:** Yara (Developer / CRUD template), Sara (fixed QA suite), Jood (frontend + PM agent), Alanoud (orchestrator)
**Source of truth:** [`../schema.py`](../schema.py) (Pydantic). [`architecture.schema.proposal.json`](architecture.schema.proposal.json) is generated from it; do not edit by hand.

### Fix in v0.3.1 (integration review before merge)

| Problem | Fix |
|---|---|
| When two acceptance criteria quoted **different** texts for the same message or button (e.g. a confirmed and a cancelled delete, or two validation criteria on one field), the document kept the last text but `verbatim_messages` kept the first, so `build_architecture` raised a pydantic `ValidationError` on BA-valid input. | Each target is set once: the **first** criterion wins in both places, and a later different quote only adds a warning naming both criteria. |
| A cancelled-delete criterion (`clicks "Delete" … clicks "Cancel"`) could set `confirm_button` to "Cancel". | A second button that cancels (Cancel / Keep / No / إلغاء / تراجع) sets `cancel_delete_button` instead. |

Verified: 1,891 BA-valid variants of the 6 ready samples (quoted messages, extra field types, read options, delete wording) all produce a valid architecture and a generated app with the Developer Agent (PR #10); 0 crashes (was 1,588). Fixtures synced with PR #8; 50 tests.

### Changes in v0.3.0 (review of PR #4 by Ghala)

| Review point | Change |
|---|---|
| Validation messages were generic | Every field rule has its own message in `fields[].messages` (§6). |
| Messages must follow the acceptance criteria | Rule **M1**: text quoted in an acceptance criterion is copied verbatim and listed in `verbatim_messages` (§6). |
| Empty-list wording | Default is now neutral (`لا توجد سجلات بعد.` / `No records yet.`); a quoted AC text overrides it. |
| No message when search finds nothing | New `messages.no_results` and testid `no-results`. |
| Delete confirmation text/button differ from AC | Taken from the AC when quoted (`confirm_delete`, `delete_button`, `confirm_button`). |
| Prices need two decimals | Numbers have `display_format.decimals`: `2` for decimal, `0` for integer. |
| Required dropdown without default (Sara) | Enum fields without a default get `empty_option`, so the select starts empty and the required check can fail. |
| Sync with `main` | Fixtures = all 9 Business Analyst samples on `main`; samples regenerated; 47 tests. |

---

## 1. Principles

1. **Names are copied, never invented.** Entity `name`, field `name`, `label`, `type`, `required`, `unique`, `default` and every `validation` rule come from requirements.json unchanged.
2. **Structure only.** No HTML, CSS or `data-testid` in this file. The template derives testids from field names by the fixed rules in §5.
3. **Deterministic first.** [`../from_requirements.py`](../from_requirements.py) derives the whole document in code. Same input → same output.
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
| `fields[].enum_values` | `options: [{value, label}]` (Arabic values are their own label; English values are humanized) |
| enum without `default` | `empty_option` = `اختر <label>` / `Select <label>` |
| integer / decimal | `step` = `1` / `0.01`; `display_format.decimals` = `0` / `2` |
| `fields[].validation` | `validation` (same keys; nulls dropped) + one message per rule in `messages` |
| `crud.read.list_fields` | `table.columns` and `fields[].show_in_list` |
| `crud.read.search_fields` | `search` component (text fields only) |
| `crud.read.filter_fields` | `filters` component (enum / boolean / date only) |
| `crud.read.sort_field/direction` | `table.sort` |
| `crud.delete.requires_confirmation` | `behaviors.delete_confirmation` = `inline` / `none` |
| any `unique` field | `behaviors.check_unique_before_save = true` |
| `acceptance_criteria[]` quoted texts | `verbatim_messages` + the message/label they set (§6) |
| `functional_requirements[]` with `category: "other"` | `deferred_rules` (not built in MVP; PM records them as risks) |

## 3. Document shape

```text
schema_version     "0.3.0-proposal"
source             { requirements_schema_version }
app                { name, description, language, direction }
entity             { name, label, plural_label, display_field, storage{...}, fields[ ≤12 ] }
  fields[]         name, label, type, input, required, unique, default?, options?, empty_option?,
                   step?, display_format?, validation, messages, show_in_list
screens            [ list, form ]
  list             header, add_button, search?, filters?, table{columns, sort?, row_actions}, empty_state
  form             form_fields (every field, in order), save_button, cancel_button; modes [create, edit]
navigation         initial_screen "list"; transitions add/edit → form, save_success/cancel → list
behaviors          validate_before_save, check_unique_before_save, prefill_form_on_edit, load_on_start,
                   delete_confirmation (inline | none), after_save, after_delete
messages           empty, no_results, invalid, created, updated, deleted, confirm_delete,
                   confirm_button, cancel_delete_button, edit_button, delete_button
verbatim_messages  [{ path, text, source }]
deferred_rules     [{ requirement_id, description }]
warnings           [ string ]
```

`messages.confirm_delete` may contain `{display}`; the app replaces it with the record's `display_field` value.
Inline confirmation means an in-page confirm button, **never** `window.confirm()`, so Playwright needs no dialog handling.

## 4. When the Architect refuses

`build_architecture` raises `ArchitectureError(reasons)` (CLI exit code `1`) when:

- `status` is not `ready_for_review` (the orchestrator must also have recorded user approval);
- there is not exactly one entity;
- any field is a `reference`;
- any CRUD operation is disabled;
- the entity has more than 12 fields.

Example (`inventory_manager_ar` sample):

```text
- MVP supports exactly one entity, got 2: ['Category', 'Item']
- entity 'Item' has reference fields ['category']; relations are out of MVP scope
```

## 5. `data-testid` rules (used by Sara's suite, PR #7)

| Element | `data-testid` |
|---|---|
| Screens | `screen-list`, `screen-form` |
| Add / save / cancel | `btn-add`, `btn-save`, `btn-cancel` |
| Search box | `search-input` |
| Filter control of a field | `filter-<field>` |
| Table / one row | `records-table` / `record-row` (+ `data-id="<id>"`) |
| Cell of a field | `cell-<field>` (shows the option **label** for enums, `display_format` for numbers) |
| Row actions | `btn-edit`, `btn-delete` |
| Inline delete confirm / cancel | `btn-confirm-delete`, `btn-cancel-delete` |
| Delete confirmation text | `confirm-delete-text` |
| Empty state (no records at all) | `empty-state` |
| **No search/filter results (new)** | `no-results` |
| Input / error of a field | `input-<field>`, `error-<field>` |
| Success / info message | `toast` |

## 6. Messages

### Rule M1 (proposed by Ghala, implemented here)

1. **If the acceptance criteria quote a text, it is used verbatim.** The Architect copies it into the matching message or button and records it in `verbatim_messages` with the AC id. **QA compares these exactly.**
2. **Every other message comes from one fixed template per rule** (below). Wording is identical across apps, and **QA only checks that the message is visible** in the right place (`error-<field>`, `empty-state`, `no-results`, …).
3. **Data formats are explicit** (`display_format`), and QA checks them.

### How a quoted text is recognised

| In the acceptance criterion | Sets |
|---|---|
| `clicks "X"` / `يضغط "X"` in a create/update/validation `when` (most frequent) | `screens.form.save_button` |
| first `clicks "X"` in a delete `when` / second one when it confirms | `messages.delete_button` / `messages.confirm_button` |
| `message "X"` / `رسالة "X"` in a `read` `then`, no-records wording | `messages.empty` |
| same, when the `when` is a search or filter | `messages.no_results` |
| same, in a `delete` criterion about confirmation | `messages.confirm_delete` |
| same, in a `validation` criterion that quotes a field label (`"Title"`) | that field's rule: `required` if the `when` leaves it empty, otherwise the rule the entered value breaks |

A quoted message that is not tied to one field rule (e.g. AC-8 *"This time slot is already booked"*) is **not** attached to any field; it goes to `warnings` because it is a business rule the MVP template cannot enforce.

### Default templates

| Rule | Arabic | English |
|---|---|---|
| required | `<label>: هذا الحقل مطلوب` | `<label> is required` |
| unique | `<label>: هذه القيمة مستخدمة مسبقًا` | `<label> is already in use` |
| min_length | `<label>: يجب إدخال <n> أحرف على الأقل` | `<label> must be at least <n> characters` |
| max_length | `<label>: الحد الأقصى <n> حرفًا` | `<label> must be at most <n> characters` |
| min_value / max_value | `<label>: أقل/أعلى قيمة مسموحة <n>` | `<label> must be <n> or more/less` |
| pattern | `<label>: الصيغة غير صحيحة` | `<label> format is invalid` |
| date_constraint | `<label>: لا يمكن اختيار تاريخ سابق/لاحق` | `<label> cannot be in the past/future` |
| empty | `لا توجد سجلات بعد.` | `No records yet.` |
| no_results | `لا توجد نتائج مطابقة للبحث.` | `No records match your search.` |

The Arabic `label: message` form keeps the grammar right for any label (no gender or definiteness agreement).

## 7. Decisions on Ghala's open points

| # | Decision | Answer |
|---|---|---|
| D3 | Who adds `id`, `created_at`, `updated_at`? | The generated app, listed in `entity.storage.system_fields`. |
| D5 | localStorage key naming | `bunyan_<entity snake_case>`, one key holding a JSON array. |
| D6 | Deleting referenced records | Not applicable in the MVP: references are refused (§4). |

## 8. Requests to the Business Analyst contract

1. **One entity, no `reference`, in v0.1.** `inventory_dialect_ar` already follows this ✅. `inventory_manager_ar` still has two entities and is refused.
2. **Display labels for English enum values.** Arabic apps with values like `to_do` get a warning. Proposal: `enum_labels: {"to_do": "قيد الانتظار"}`.
3. **Business rules vs field rules.** Rules that `fields[].validation` cannot express (no double booking) should be `category: "other"` so they land in `deferred_rules` instead of a warning.
4. **Quote exact texts in acceptance criteria** when the user asks for them (`the message "…" is shown`, `clicks "…"`), otherwise describe the outcome without quotes. That is what rule M1 keys on.

## 9. Open questions

| # | Question | Who |
|---|---|---|
| A1 | Does the template support every `input` control in §2 (especially `datetime-local`, `checkbox`, `url`), `empty_option` and `display_format`? | Yara |
| A2 | Compare `verbatim_messages` exactly and the rest by visibility (rule M1)? Add `no-results` and `confirm-delete-text` to the suite? | Sara |
| A3 | Replace the placeholder `ArchitectureModel` in `backend/schemas/contracts.py` (PR #5) with this contract and add the architect stage after approval. | Alanoud |
| A4 | Use `samples/outputs/*.architecture.json` instead of `mockArchitecture`, with storage key `bunyan_<entity>` (F6). | Jood |
