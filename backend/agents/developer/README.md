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
An LLM-based repair is not implemented. Tests: `tests/test_repair_loop.py` (offline and real Chromium).
