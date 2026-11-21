"""Quality log: adds one line per QA run (pass rate, run time, failed checks)."""

import csv
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[3] / "tests" / "e2e" / "reports" / "quality_log.csv"

COLUMNS = [
    "finished_at",
    "app",
    "entity",
    "attempt",
    "is_harness_fixture",
    "passed",
    "total",
    "pass_rate",
    "duration_ms",
    "failed_checks",
]


def append_run(report, log_path=LOG_PATH):
    """Adds one line for this run to the CSV log and returns that line."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    is_new_file = not log_path.exists()

    row = {
        "finished_at": report["run"]["finished_at"],
        "app": (report.get("app") or {}).get("name"),
        "entity": report.get("entity"),
        "attempt": report["run"]["attempt"],
        "is_harness_fixture": report["inputs"]["is_harness_fixture"],
        "passed": report["summary"]["passed"],
        "total": report["summary"]["total"],
        "pass_rate": report["summary"]["pass_rate"],
        "duration_ms": report["run"]["duration_ms"],
        "failed_checks": ";".join(c["id"] for c in report["checks"] if c["status"] == "failed"),
    }

    # utf-8-sig on a new file so Excel shows Arabic app names correctly
    encoding = "utf-8-sig" if is_new_file else "utf-8"
    with open(log_path, "a", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if is_new_file:
            writer.writeheader()
        writer.writerow(row)
    return row