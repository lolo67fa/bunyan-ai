"""Command-line entry point. Run from the repository root:

    python -m backend.agents.project_manager --input backend/agents/project_manager/samples/inputs/inventory_dialect_ar.json
    python -m backend.agents.project_manager --requirements req.json --architecture arch.json \\
        --test-report report.json --status documenting --out-dir output/demo
    python -m backend.agents.project_manager --input ... --mode llm
    python -m backend.agents.project_manager --schema

Exit codes: 0 success, 1 invalid input, 2 usage or configuration error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .agent import run_project_manager, write_outputs
from .config import ConfigError
from .schema import PMInput, json_schema


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    _utf8_console()
    p = argparse.ArgumentParser(prog="python -m backend.agents.project_manager",
                                description="BUNYAN AI Project Manager Agent")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=Path, help="One JSON file matching the PMInput contract.")
    src.add_argument("--requirements", type=Path, help="requirements.json (with the options below).")
    src.add_argument("--schema", action="store_true", help="Print the input and output JSON Schemas.")
    p.add_argument("--architecture", type=Path, help="architecture.json")
    p.add_argument("--test-report", type=Path, help="test_report.json")
    p.add_argument("--status", default="documenting", help="Workflow status (default: documenting).")
    p.add_argument("--files", nargs="*", default=None, help="Generated files, e.g. index.html style.css app.js")
    p.add_argument("--repair-attempt", type=int, default=0)
    p.add_argument("--run-time", type=float, help="Whole pipeline run time in seconds.")
    p.add_argument("--language", choices=["ar", "en"], help="Document language (default: the requirements' language).")
    p.add_argument("--mode", choices=["rules", "llm", "mock"], help="Overrides PM_MODE (default: rules).")
    p.add_argument("--out-dir", type=Path, help="Write project_plan.md and risks.md here (default: print the plan).")
    p.add_argument("--json", action="store_true", help="Print the full result as JSON instead of the plan.")
    a = p.parse_args(argv)

    if a.schema:
        print(json.dumps(json_schema(), indent=2, ensure_ascii=False))
        return 0
    try:
        if a.input:
            data = _read_json(a.input)
        else:
            data = {
                "requirements": _read_json(a.requirements),
                "architecture": _read_json(a.architecture) if a.architecture else None,
                "test_report": _read_json(a.test_report) if a.test_report else None,
                "status": a.status,
                "generated_files": a.files if a.files is not None else [],
                "repair_attempt": a.repair_attempt,
                "run_time_seconds": a.run_time,
            }
        if a.language:
            data["language"] = a.language
        pm_input = PMInput.model_validate(data)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read input: {exc}", file=sys.stderr)
        return 2
    except ValidationError as exc:
        print("INVALID INPUT:", file=sys.stderr)
        for e in exc.errors():
            print(f"  - {'.'.join(str(x) for x in e['loc'])}: {e['msg']}", file=sys.stderr)
        return 1

    try:
        result = run_project_manager(pm_input, mode=a.mode)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    for w in result.warnings:
        print(f"warning: {w}", file=sys.stderr)
    open_risks = sum(1 for r in result.risks if r.status == "open")
    print(f"mode: {result.mode}   language: {result.language}   status: {result.status}   "
          f"risks: {len(result.risks)} ({open_risks} open)", file=sys.stderr)

    if a.out_dir:
        paths = write_outputs(result, a.out_dir)
        for name, path in paths.items():
            print(f"wrote {path}", file=sys.stderr)
    elif a.json:
        print(result.model_dump_json(indent=2))
    else:
        print(result.project_plan_md)
        print(result.risks_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
