"""Rebuild samples/outputs/<name>/project_plan.md and risks.md from samples/inputs (rules mode).

    python -m backend.agents.project_manager.regenerate_samples
"""

from __future__ import annotations

import json
from pathlib import Path

from .agent import run_project_manager, write_outputs
from .config import Settings

SAMPLES = Path(__file__).resolve().parent / "samples"


def main() -> None:
    settings = Settings(mode="rules", provider=None, model=None)
    for path in sorted((SAMPLES / "inputs").glob("*.json")):
        result = run_project_manager(json.loads(path.read_text(encoding="utf-8")), settings=settings)
        write_outputs(result, SAMPLES / "outputs" / path.stem)
        print(f"{path.stem}: {result.status}, {len(result.risks)} risks")


if __name__ == "__main__":
    main()
