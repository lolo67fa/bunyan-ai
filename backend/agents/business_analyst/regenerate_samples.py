"""Regenerate the committed mock sample outputs and the exported JSON Schema.

    python backend/agents/business_analyst/regenerate_samples.py

Run it after changing ``schema.py`` or ``mock_analyst.py``; the offline tests
fail while the committed files are stale. Mock mode only — never calls an LLM.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
# Replace this folder (which has generic names like config.py) with the repo root on sys.path.
sys.path[0] = str(AGENT_DIR.parents[2])

from backend.agents.business_analyst import AnalystInput, analyze_input, json_schema  # noqa: E402


def main() -> None:
    contract = AGENT_DIR / "contract" / "requirements.schema.proposal.json"
    contract.parent.mkdir(exist_ok=True)
    contract.write_text(json.dumps(json_schema(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {contract.relative_to(AGENT_DIR)}")

    out_dir = AGENT_DIR / "samples" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted((AGENT_DIR / "samples" / "inputs").glob("*.json")):
        request = AnalystInput.model_validate_json(path.read_text(encoding="utf-8"))
        doc = analyze_input(request, mode="mock")
        target = out_dir / f"{path.stem}.requirements.json"
        target.write_text(doc.model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(f"wrote {target.relative_to(AGENT_DIR)}  ({doc.status})")


if __name__ == "__main__":
    main()
