"""CLI.

  python -m backend.agents.architect --input requirements.json [--out architecture.json]
  python -m backend.agents.architect --validate architecture.json
  python -m backend.agents.architect --schema

Exit codes: 0 ok, 1 requirements not usable / architecture invalid, 2 usage error.
"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from . import ArchitectureDocument, ArchitectureError, build_architecture, json_schema


def main() -> int:
    p = argparse.ArgumentParser(prog="python -m backend.agents.architect")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--input", help="approved requirements.json")
    g.add_argument("--validate", help="architecture.json to check against the contract")
    g.add_argument("--schema", action="store_true", help="print the JSON Schema")
    p.add_argument("--out", help="write architecture.json here instead of stdout")
    a = p.parse_args()

    if a.schema:
        print(json.dumps(json_schema(), ensure_ascii=False, indent=2))
        return 0
    if a.validate:
        try:
            ArchitectureDocument.model_validate_json(Path(a.validate).read_text(encoding="utf-8"))
        except ValidationError as exc:
            print(f"INVALID\n{exc}", file=sys.stderr)
            return 1
        print("VALID", file=sys.stderr)
        return 0

    req = json.loads(Path(a.input).read_text(encoding="utf-8"))
    try:
        doc = build_architecture(req)
    except ArchitectureError as exc:
        print("Cannot build an MVP architecture from these requirements:", file=sys.stderr)
        for r in exc.reasons:
            print(f"  - {r}", file=sys.stderr)
        return 1
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out} ({len(doc['warnings'])} warning(s))", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
