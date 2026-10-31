# Business Analyst Agent

**Owner:** Ghala Alshreef · **Branch:** `feature/ghala-analyst` · **Output:** `requirements.json`

The first agent in the BUNYAN AI workflow. It turns an application idea, in **Arabic or English**, into structured, validated requirements for a CRUD web app. It:

- identifies the **entities** and their **fields**, with field types and validation rules;
- defines which **Create / Read / Update / Delete** operations each entity supports (with list columns, search, filters and sorting);
- writes **functional requirements**, **user stories** and **measurable acceptance criteria** (Given / When / Then with concrete values);
- asks **clarification questions** when the idea is too vague (blocking) or when a reasonable default was assumed (optional);
- **flags or rejects** features outside the CRUD MVP (login, payments, mobile apps, servers, real-time, messaging, uploads, ERP/CRM).

It runs **on its own**: it does not need the Architect, Developer, QA or Project Manager agents, the orchestrator, or the frontend.

> **Contract status: PROPOSAL.** No shared `requirements` schema has been approved in `backend/schemas/` yet, so this agent uses a provisional contract kept in this folder: [`contract/CONTRACT.md`](contract/CONTRACT.md). Nothing in `backend/schemas/` was changed.

---

## Folder layout

```
business_analyst/
├── README.md                 ← this file
├── contract/
│   ├── CONTRACT.md           ← input/output contract (for Naifah, Sara, Yara, Alanoud)
│   ├── INTEGRATION.md        ← handoff guide for the Architect and the orchestrator
│   └── requirements.schema.proposal.json   ← generated JSON Schema
├── schema.py                 ← Pydantic models = source of truth of the contract
├── analyst.py                ← pipeline: generate → parse → validate → scope guard (+ LLM retry loop)
├── crew.py                   ← CrewAI agent / task / crew (LLM mode, crewai backend)
├── direct_llm.py             ← Anthropic SDK call (LLM mode, direct backend)
├── prompts.py                ← role, goal, backstory, task prompt
├── mock_analyst.py           ← offline mock "LLM" (template-based, 3 demo domains)
├── scope.py                  ← deterministic CRUD-scope guard (English + Arabic)
├── language.py               ← Arabic / English detection
├── config.py                 ← environment variables
├── __main__.py               ← command line interface
├── regenerate_samples.py     ← rebuilds samples/outputs and the JSON Schema
├── samples/
│   ├── inputs/               ← task manager, inventory (Arabic + Gulf dialect), appointment booking, vague, out-of-scope
│   ├── answers/              ← example answers to clarification questions
│   └── outputs/              ← requirements.json produced in mock mode ← give these to the Architect
├── tests/                    ← OFFLINE mock tests (free, always run)
├── evals/                    ← LIVE LLM evaluations (paid, opt-in)
├── requirements.txt          ← mock mode + tests
├── requirements-llm.txt      ← + CrewAI for LLM mode
└── .env.example              ← agent-specific environment variables
```

## Setup

Python 3.10 – 3.13. Run every command from the **repository root** (`bunyan-ai/`).

```bash
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

# Mock mode and tests only (small, no API key needed):
pip install -r backend/agents/business_analyst/requirements.txt

# Add CrewAI for real LLM runs (large, ~150 packages; uv is much faster than pip on slow connections):
pip install uv
uv pip install --python .venv/Scripts/python.exe -r backend/agents/business_analyst/requirements-llm.txt
```

## Two modes

| | **Mock mode** (default) | **LLM mode** |
|---|---|---|
| Select | `BA_MODE=mock` or `--mode mock` | `BA_MODE=llm` or `--mode llm` |
| Cost | Free, offline, deterministic | Uses your API credits |
| What generates the JSON | `mock_analyst.py`: keyword match on 3 demo domains + hand-written English/Arabic templates | CrewAI agent + your configured model |
| Validation, scope guard | **Same pipeline** | **Same pipeline** + automatic retry with the validation errors |
| Use it for | Testing the contract, the pipeline and integration with other agents | Real analysis of new ideas |

Mock mode is **not** a real analysis. It only knows task managers, inventory managers and appointment booking. Any other idea gets `needs_clarification` (or `rejected_out_of_scope`). Its value is producing valid, realistic `requirements.json` files for free.

## Run it

```bash
# Mock mode (default): print requirements.json to the terminal
python -m backend.agents.business_analyst --idea "A task manager with due dates and priorities"

# From a sample input file, saving the output
python -m backend.agents.business_analyst \
  --input backend/agents/business_analyst/samples/inputs/inventory_manager_ar.json \
  --out output/requirements.json

# Clarification loop: vague idea → questions → answers → requirements
python -m backend.agents.business_analyst --input backend/agents/business_analyst/samples/inputs/vague_idea_en.json
python -m backend.agents.business_analyst --input backend/agents/business_analyst/samples/inputs/vague_idea_en.json \
  --answers backend/agents/business_analyst/samples/answers/vague_idea_answers.json

# Validate any requirements.json (for example one written by hand or by another tool)
python -m backend.agents.business_analyst --validate backend/agents/business_analyst/samples/outputs/task_manager_en.requirements.json

# Print the JSON Schema of the output contract
python -m backend.agents.business_analyst --schema
```

The JSON goes to stdout (or `--out`); a short summary (status, entities, counts, questions, out-of-scope items) goes to stderr.
Exit codes: `0` success · `1` analysis/validation failed · `2` configuration or usage error.
`output/` is git-ignored, so it is a safe place for generated files.

### LLM mode

**1. Put your API key in the git-ignored `.env` file (never in code, chat, issues or commits).**

```powershell
# from the repository root
Copy-Item .env.example .env        # .env is listed in .gitignore
notepad .env                       # type the values below, save, close
git check-ignore .env              # must print ".env" (confirms it will not be committed)
```

```dotenv
LLM_PROVIDER=anthropic
LLM_MODEL=claude-opus-5-5
ANTHROPIC_API_KEY=<your key from console.anthropic.com>
```

Use a key with a spending limit set in the Anthropic Console. To use a different model for this agent only, set `BA_LLM_PROVIDER` / `BA_LLM_MODEL` (see [`.env.example`](.env.example)). With the CrewAI backend any LiteLLM provider works (for example `openai` with `OPENAI_API_KEY`).

**2. Choose a backend** (`BA_LLM_BACKEND`):

| Backend | Needs | Use it for |
|---|---|---|
| `crewai` (default) | `requirements-llm.txt` (CrewAI 1.15.23 + its Anthropic extra; ~150 packages, see Setup) | The real integration path used by the orchestrator |
| `direct` | only the `anthropic` package (`pip install anthropic`; works with SDK 0.73 as pinned by CrewAI and with 1.x) | Validating the prompt, model and validation pipeline with a real model when CrewAI is not installed. Anthropic models only |

Both send the same prompt and go through the same parsing, Pydantic validation, scope guard and retry loop. Only the code that calls the model differs.

**3. Run** (PowerShell; the `$env:` lines apply to the current terminal only):

```powershell
$env:BA_LLM_BACKEND = "direct"     # omit to use CrewAI
python -m backend.agents.business_analyst --mode llm `
  --input backend/agents/business_analyst/samples/inputs/inventory_dialect_ar.json `
  --out output/inventory_dialect_ar.llm.requirements.json
python -m backend.agents.business_analyst --validate output/inventory_dialect_ar.llm.requirements.json
```

If the model returns invalid JSON or breaks a rule (for example a vague acceptance criterion or a login requirement), the agent sends the exact validation errors back to the model and retries, `BA_MAX_RETRIES` times (default 2). It never returns an invalid document; it exits with code 1 instead.

Notes:
- `temperature` / `top_p` / `top_k` are **not sent** to Anthropic: the Messages API rejects them (API version `2026-10-21`). `BA_TEMPERATURE` is only forwarded to other providers.
- The direct backend sets `output_config.effort` from `BA_EFFORT` (default `high`) and enables the server-side refusal fallback (`fallbacks: "default"`) on models that support it.

### From Python (for the orchestrator)

```python
from backend.agents.business_analyst import analyze, RequirementsDocument

idea = "أريد تطبيقاً لإدارة المخزون"
doc = analyze(idea, mode="mock")                                # or mode="llm"
if doc.status == "needs_clarification":
    questions = [q.question for q in doc.clarification_questions if q.blocking]
    doc = analyze(idea, answers={"Q-1": "...", "Q-2": "..."})
requirements_json = doc.model_dump_json(indent=2)
```

`crew.build_agent(settings)` and `crew.build_task(description, agent)` are available if the orchestrator wants to place this agent in a larger CrewAI crew.

## Tests

| | Folder | Calls an LLM? | Run with |
|---|---|---|---|
| **Mock tests** | `tests/` | **Never.** Forces mock mode, hides API keys, uses fake models. | `pytest backend/agents/business_analyst/tests` |
| **LLM evaluations** | `evals/` | Yes, opt-in. Skipped unless `BA_RUN_LLM_EVALS=1` and a model + key are configured. | see below |

```bash
# Offline mock tests: schema validity, missing information, CRUD scope, pipeline, CLI
pytest backend/agents/business_analyst/tests

# Live LLM evaluations (costs money: 6 samples, 1 to 3 model calls each)
# PowerShell:  $env:BA_RUN_LLM_EVALS="1"; pytest backend/agents/business_analyst/evals -v
BA_RUN_LLM_EVALS=1 pytest backend/agents/business_analyst/evals -v
```

What the mock tests cover:

- `test_schema.py`: all sample outputs validate; JSON round trip; 25 kinds of broken documents are rejected (bad IDs, dangling references, type/rule mismatches, missing CRUD coverage, vague criteria in English and Arabic, and more).
- `test_missing_information.py`: vague ideas (English/Arabic) give `needs_clarification` with blocking questions; answers resolve them; a `ready_for_review` document cannot keep blocking questions.
- `test_scope.py`: the guard detects 8 out-of-scope categories in English and Arabic without flagging plain CRUD ideas; mixed ideas keep the CRUD core; fully out-of-scope ideas are rejected; an LLM answer that sneaks a login or payment requirement in is rejected.
- `test_direct_backend.py`: the direct Anthropic backend with a **fake client**: no sampling parameters sent, effort and fallback set, refusal / truncation handling, dialect input end to end.
- `test_architect_handoff.py`: a reference consumer derives storage keys, form inputs, validation attributes, list/search/filter/sort and RTL from every ready sample, the way the Architect would.
- `test_pipeline.py`: LLM mode with a **fake** model (retry with errors, give-up after max retries, code-fence tolerance), configuration and model overrides, CLI exit codes, and a check that committed samples and JSON Schema are up to date.

The evals check behaviour (status, language, expected entity, flagged scope categories) rather than exact wording, and save every output plus a timing report to `evals/output/` (git-ignored).

## For the Software Architect Agent (Naifah)

- **Start here:** [`contract/INTEGRATION.md`](contract/INTEGRATION.md) (interface, mapping to architecture, open decisions)
- Contract: [`contract/CONTRACT.md`](contract/CONTRACT.md) · JSON Schema: [`contract/requirements.schema.proposal.json`](contract/requirements.schema.proposal.json)
- Ready-to-use inputs: [`samples/outputs/task_manager_en.requirements.json`](samples/outputs/task_manager_en.requirements.json), [`inventory_manager_ar.requirements.json`](samples/outputs/inventory_manager_ar.requirements.json) (Arabic, two entities with a `reference` field), [`appointment_booking_en.requirements.json`](samples/outputs/appointment_booking_en.requirements.json)
- Validate in Python: `RequirementsDocument.model_validate_json(text)`. Only run when `status == "ready_for_review"` **and** the user has approved.

## After changing the schema or mock templates

```bash
python backend/agents/business_analyst/regenerate_samples.py
pytest backend/agents/business_analyst/tests
```

## Known limitations

- **LLM mode has not been run against a real model yet: no API key was available.** CrewAI 1.15.23 is installed and verified up to the network: both backends build a valid request that reaches Anthropic and is rejected only for the missing key (HTTP 401). Status per check: [`contract/INTEGRATION.md`](contract/INTEGRATION.md) §5.
- Mock mode recognises only the three demo domains; it is for testing, not analysis.
- The scope guard is keyword-based. It can miss unusual phrasings, and the LLM is the first line of defence. It is tuned to avoid flagging CRUD data such as a `payment_status` field or a library "checkout".
- `feedback` (revision after user review) is only used in LLM mode.
- The contract is a proposal until the team approves it (see the open points in `CONTRACT.md`).
