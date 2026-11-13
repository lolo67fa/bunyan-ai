# Project Manager Agent

**Branch:** `feature/jood-project-manager` · **Outputs:** `project_plan.md`, `risks.md`

The last agent in the BUNYAN AI workflow. After the other agents finish, it collects their outputs and writes two documents for the user:

- **`project_plan.md`**: scope (what is included and left out), the five stages with owner, output and status, a basic timeline against the 90-second target, project status, and the list of deliverables.
- **`risks.md`**: a risk table (likelihood, impact, mitigation, open or closed) and where each risk comes from.

It **only reads** its inputs and **only writes** these two files. It never edits code or another agent's output. The documents are written in the app's language (Arabic or English), the same order as the platform's Plan screen.

> **Contract status: PROPOSAL** (`0.1.0-proposal`). See [`contract/CONTRACT.md`](contract/CONTRACT.md).

## Inputs

| Input | From | Required |
|---|---|---|
| `requirements.json` | Business Analyst | yes |
| `architecture.json` | Architect | no |
| `test_report.json` (latest run) | QA Tester | no |
| generated file names, repair attempts, run time, stage durations, workflow status | Orchestrator | no |

Missing inputs are fine: when a run stops early the agent still writes a plan, marked `partial`, that says where it stopped.

## Two modes

| | **Rules mode** (default) | **LLM mode** |
|---|---|---|
| Select | `PM_MODE=rules` or `--mode rules` (`mock` also works) | `PM_MODE=llm` or `--mode llm` |
| Cost | Free, offline, deterministic | One short Anthropic request per run |
| What it does | Reads the facts, builds the stage table, applies the risk rules, writes both documents | Same, plus an executive summary written by the model and up to 3 extra risks |
| Safety | — | The model sees only the collected facts; its answer is validated; it cannot change numbers, stages or rule risks. If the call fails, the rule-based documents are kept with a warning. |

Rules mode is a complete agent, not a placeholder: every number and risk comes from the other agents' outputs.

## Setup

Python 3.10 – 3.13, from the **repository root**:

```bash
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

pip install -r backend/agents/project_manager/requirements.txt        # rules mode + tests
pip install -r backend/agents/project_manager/requirements-llm.txt    # adds LLM mode (small: Anthropic SDK only)
```

## Run it

```bash
# A sample run: print the plan and the risks
python -m backend.agents.project_manager --input backend/agents/project_manager/samples/inputs/inventory_dialect_ar.json

# Write project_plan.md and risks.md to a folder (output/ is git-ignored)
python -m backend.agents.project_manager --input backend/agents/project_manager/samples/inputs/inventory_dialect_ar.json --out-dir output/pm-demo

# From separate files, as the orchestrator will have them
python -m backend.agents.project_manager \
  --requirements requirements.json --architecture architecture.json --test-report test_report.json \
  --files index.html style.css app.js --repair-attempt 1 --run-time 62 --out-dir output/pm-demo

# Full result as JSON (stages, risks, summary, both documents)
python -m backend.agents.project_manager --input ... --json

# Input and output JSON Schemas
python -m backend.agents.project_manager --schema
```

Exit codes: `0` success · `1` invalid input · `2` usage or configuration error. A one-line summary goes to stderr.

### LLM mode

Put the key in the git-ignored `.env` at the repository root (never in code or chat):

```dotenv
LLM_PROVIDER=anthropic
LLM_MODEL=claude-opus-5-5
ANTHROPIC_API_KEY=<your key>
```

```bash
python -m backend.agents.project_manager --input backend/agents/project_manager/samples/inputs/task_manager_en.json --mode llm
```

## Use it from the orchestrator

```python
from backend.agents.project_manager import run_project_manager, write_outputs

result = run_project_manager({
    "project_id": project_id,
    "status": "documenting",
    "requirements": requirements,          # dict
    "architecture": architecture,          # dict or None
    "test_report": test_report,            # dict or None (latest run)
    "generated_files": ["index.html", "style.css", "app.js"],
    "repair_attempt": 1,
    "run_time_seconds": 62,
    "stage_seconds": {"structure": 9, "development": 24, "tests": 21},
})
write_outputs(result, f"output/{project_id}")   # project_plan.md, risks.md
# result.summary, result.stages, result.risks are also available for the API response
```

## Samples

`samples/inputs/` are built from real outputs: the Business Analyst's `requirements.json` samples, the Architect's `architecture.json` samples (PR #4), and test reports in the QA contract shape (PR #7, validated against its `QAReport` model).

| Sample | Shows |
|---|---|
| `inventory_dialect_ar` | Complete run in Arabic, one check repaired (closed risk), timeline within target |
| `task_manager_en` | Complete run in English, all checks passed first time |
| `appointment_tests_failing_en` | A check still failing after two repairs, an Architect warning, run time above target |
| `stopped_at_structure_ar` | Run stopped at the structure stage: partial plan |

`samples/outputs/<name>/` holds the documents the agent writes for each. After changing the agent, rebuild them:

```bash
python -m backend.agents.project_manager.regenerate_samples
```

## Tests

```bash
cd backend/agents/project_manager
python -m pytest
```

Offline and free: LLM mode is tested with a fake client, and any real key is hidden during tests.

## Files

```
project_manager/
├── agent.py            ← run_project_manager(), write_outputs()
├── schema.py           ← input/output contract (Pydantic)
├── facts.py            ← reads requirements, architecture and test report into plain facts
├── risks.py            ← deterministic risk rules
├── render.py           ← stage table, project_plan.md, risks.md (Arabic and English)
├── arabic.py           ← Arabic number agreement (حقلان، 3 حقول، 11 حقلاً)
├── llm.py              ← optional LLM summary and extra risks
├── config.py           ← PM_* environment variables
├── __main__.py         ← command line
├── regenerate_samples.py
├── contract/CONTRACT.md
├── samples/            ← inputs/ and outputs/
└── tests/
```
