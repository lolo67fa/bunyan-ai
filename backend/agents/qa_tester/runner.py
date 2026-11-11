"""QA Tester Agent: runs the fixed Playwright suite in tests/e2e."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from .quality_log import append_run
from .schema import QAReport

REPO_DIR = Path(__file__).resolve().parents[3]
E2E_DIR = REPO_DIR / "tests" / "e2e"
REPORT_PATH = E2E_DIR / "reports" / "test_report.json"


def run_qa(app_dir, requirements_path, attempt=0, app_path="/", architecture_path=None):
    """Runs the 8 checks on one app and returns test_report.json as a dict."""
    app_dir = Path(app_dir).resolve()
    requirements_path = Path(requirements_path).resolve()

    if not (app_dir / "index.html").exists():
        raise FileNotFoundError(f"No index.html in {app_dir}")
    if not requirements_path.exists():
        raise FileNotFoundError(f"requirements.json not found: {requirements_path}")
    if architecture_path is not None:
        architecture_path = Path(architecture_path).resolve()
        if not architecture_path.exists():
            raise FileNotFoundError(f"architecture.json not found: {architecture_path}")
    if attempt not in (0, 1, 2):
        raise ValueError("attempt must be 0 (first run), 1 or 2 (re-test after a repair)")

    npx = shutil.which("npx")
    if npx is None:
        raise RuntimeError("npx not found. Install Node.js first.")

    # Tell the test suite what to test
    env = os.environ.copy()
    env["APP_DIR"] = str(app_dir)
    env["REQUIREMENTS"] = str(requirements_path)
    env["QA_ATTEMPT"] = str(attempt)
    env["APP_PATH"] = app_path
    if architecture_path is not None:
        env["ARCHITECTURE"] = str(architecture_path)
    else:
        env.pop("ARCHITECTURE", None)

    # Delete the old report so we never return results from an earlier run
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()

    completed = subprocess.run(
        [npx, "playwright", "test"],
        cwd=E2E_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )

    if not REPORT_PATH.exists():
        raise RuntimeError(
            "Playwright did not write test_report.json:\n"
            + completed.stdout[-2000:]
            + completed.stderr[-2000:]
        )

    with open(REPORT_PATH, encoding="utf-8") as f:
        report = json.load(f)

    # Stop here if the report does not have the agreed shape
    QAReport.model_validate(report)

    # Add this run to the quality log
    append_run(report)
    return report