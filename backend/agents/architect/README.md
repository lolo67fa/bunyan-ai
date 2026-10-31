# Software Architect Agent

**Owner:** Naifah · **Input:** approved `requirements.json` · **Output:** `architecture.json`
**Contract:** v0.2.0-proposal, see [`contract/CONTRACT.md`](contract/CONTRACT.md) (not yet approved).

## Status

- ✅ Contract (Pydantic) with cross-reference validation.
- ✅ Deterministic builder `build_architecture(requirements_dict)`; refuses out-of-MVP input with reasons.
- ✅ Samples generated from Ghala's Business Analyst samples (`samples/outputs/`).
- ⏳ LLM layer (enum labels, wording) and CrewAI wiring: not started.

## Use

```bash
pip install -r backend/agents/architect/requirements.txt

# requirements.json -> architecture.json
python -m backend.agents.architect --input requirements.json --out architecture.json
# check a file against the contract
python -m backend.agents.architect --validate architecture.json
# print the JSON Schema
python -m backend.agents.architect --schema

# tests (offline)
cd backend/agents/architect && pytest
```

```python
from backend.agents.architect import build_architecture, ArchitectureError

try:
    arch = build_architecture(requirements)   # dict in, validated dict out
except ArchitectureError as exc:
    print(exc.reasons)                       # why the MVP cannot build it
```
