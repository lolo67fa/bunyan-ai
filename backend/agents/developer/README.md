# Developer Agent (owner: Yara)

Deterministic: `generate(requirements, architecture, out_dir)` validates the approved contracts and
fills the CRUD template (`templates/crud`) with the architecture as escaped JSON. No LLM, no API key.

## Repair (`repair.py`)

- `restore_from_contracts(requirements, architecture, app_dir, defects, attempt)`: the strategy the
  orchestrator uses after a failed QA run. It regenerates the app the approved contracts describe in a
  temporary folder and replaces every file in `app_dir` that differs, returning `RepairChange`
  (`changed_files` with SHA-256 before/after, the defects it answered). When nothing differs it changes
  nothing, and the orchestrator neither re-tests nor counts a repair. Malformed defects raise `ValueError`.
- `run_with_repairs(...)`: the original coordination helper (at most `MAX_REPAIRS = 2`), kept for
  callers that bring their own strategy.

It fixes damaged, edited or stale generated files; it cannot fix a logic error in the template itself.
Tests: `tests/test_repair_loop.py` (offline and real Chromium).

## AI repair (`llm_repair.py`, experimental, off by default)

`make_llm_repair(owner)` is used with `BUNYAN_REPAIR=llm`. Each attempt runs `restore_from_contracts`
first. Only when that changes nothing, and only for an owner with a valid access code
(`backend/llm_access.py`), one bounded Claude request is made. The rules:

- **Input:** the app files and QA messages, sent as untrusted data in tagged blocks.
- **Output:** constrained by a JSON schema to `{diagnosis, edits[{file, find, replace}]}`.
- **Validation before anything is written:**
  - files from the allowlist only;
  - each snippet occurs exactly once;
  - size caps;
  - no network or dynamic code;
  - the approved configuration in `app.js` stays unchanged.
- **Writing:** all edits pass, or nothing is written.
- **Later attempts:** once an AI edit is applied, they build on it instead of restoring.
- **Cost:** reserved before the request and booked from the reported usage; no retries, no fallback, a timeout.

Tests: `tests/test_llm_repair.py`, with a stand-in model (no network) and one real-Chromium test. It
has not yet been run with a paid request.
