"""Command-line entry point.

Run from the repository root:

    python -m backend.agents.business_analyst --idea "A task manager with due dates"
    python -m backend.agents.business_analyst --input backend/agents/business_analyst/samples/inputs/task_manager_en.json
    python -m backend.agents.business_analyst --mode llm --idea "..." --out requirements.json
    python -m backend.agents.business_analyst --validate path/to/requirements.json
    python -m backend.agents.business_analyst --schema

Exit codes: 0 success, 1 analysis or validation failed, 2 usage/configuration error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .analyst import AnalysisError, OutputRejected, analyze_input, validate_requirements_file
from .config import ConfigError, get_settings
from .schema import AnalystInput, RequirementsDocument, json_schema


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def _summary(doc: RequirementsDocument) -> str:
    lines = [
        f"status: {doc.status}   language: {doc.language}   app: {doc.app.name}",
        f"entities: {', '.join(e.name for e in doc.entities) or '-'}",
        f"requirements: {len(doc.functional_requirements)}   stories: {len(doc.user_stories)}   "
        f"acceptance criteria: {len(doc.acceptance_criteria)}",
    ]
    for q in doc.clarification_questions:
        lines.append(f"question {q.id} ({'blocking' if q.blocking else 'optional'}): {q.question}")
    for item in doc.out_of_scope:
        lines.append(f"out of scope [{item.category}] {item.feature} -> {item.action}")
    return "\n".join(lines)


def main(argv=None) -> int:
    _utf8_console()
    parser = argparse.ArgumentParser(prog="python -m backend.agents.business_analyst",
                                     description="BUNYAN AI Business Analyst Agent")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--idea", help="Application idea (Arabic or English).")
    source.add_argument("--input", type=Path, help="JSON file matching the AnalystInput contract.")
    source.add_argument("--validate", type=Path, metavar="FILE", help="Validate an existing requirements.json.")
    source.add_argument("--schema", action="store_true", help="Print the JSON Schema of the output contract.")
    parser.add_argument("--answers", type=Path, help="JSON object of answers to clarification questions.")
    parser.add_argument("--feedback", help="User feedback asking the agent to revise the requirements.")
    parser.add_argument("--mode", choices=["mock", "llm"], help="Overrides BA_MODE (default: mock).")
    parser.add_argument("--out", type=Path, help="Write requirements.json here instead of stdout.")
    args = parser.parse_args(argv)

    if args.schema:
        print(json.dumps(json_schema(), indent=2, ensure_ascii=False))
        return 0

    if args.validate:
        try:
            doc = validate_requirements_file(args.validate.read_text(encoding="utf-8"))
        except OutputRejected as exc:
            print(f"INVALID: {args.validate}", file=sys.stderr)
            for e in exc.errors:
                print(f"  - {e}", file=sys.stderr)
            return 1
        print(f"VALID: {args.validate}\n{_summary(doc)}", file=sys.stderr)
        return 0

    try:
        if args.input:
            request = AnalystInput.model_validate_json(args.input.read_text(encoding="utf-8"))
        else:
            request = AnalystInput(idea=args.idea)
        if args.answers:
            request.answers.update(json.loads(args.answers.read_text(encoding="utf-8")))
        if args.feedback:
            request.feedback = args.feedback
        settings = get_settings(args.mode)
        print(f"Business Analyst Agent - mode: {settings.mode}"
              + (f", model: {settings.litellm_model}" if settings.mode == "llm" else ""), file=sys.stderr)
        doc = analyze_input(request, settings=settings)
    except (ConfigError, ValidationError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except AnalysisError as exc:
        print(f"ANALYSIS FAILED: {exc}", file=sys.stderr)
        return 1

    output = doc.model_dump_json(indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", encoding="utf-8")
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(output)
    print(_summary(doc), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
