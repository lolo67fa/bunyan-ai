"""QA stage of the pipeline: runs Sara's QA Tester on one generated app.

The QA agent itself (backend/agents/qa_tester, tests/e2e) is used as it is.
This module only:

- makes sure one QA run happens at a time (see ``_qa_lock``),
- stores the report and failure evidence inside the project folder,
- removes server paths from the stored report,
- turns the report into an outcome and the metrics the frontend shows.

No result is invented here: every number comes from the report Playwright wrote.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.agents.qa_tester import runner as qa_runner
from backend.agents.qa_tester.schema import QAReport

TEST_REPORT_FILE = "test_report.json"
EVIDENCE_DIRNAME = "qa_evidence"

# QA outcomes stored in project["qa"]["status"].
QA_PASSED = "passed"    # every check that ran passed, none failed
QA_FAILED = "failed"    # the suite ran and found real defects in the app
QA_BLOCKED = "blocked"  # the suite could not test the app, or crashed
QA_NOT_RUN = "not_run"  # QA is switched off for this run

QaRunner = Callable[..., Dict[str, Any]]

# The QA runner writes its report to one fixed file, serves the app on one fixed
# port and keeps screenshots in one shared folder, so two runs at the same time
# would overwrite each other. The thread lock covers this server process; the
# file lock also covers other processes on the same machine where the platform
# supports it. Runs on different machines are not coordinated.
_thread_lock = threading.Lock()
_LOCK_FILE = Path(tempfile.gettempdir()) / "bunyan-qa.lock"

try:
    import fcntl
except ImportError:  # Windows: thread lock only
    fcntl = None


class QaBlocked(Exception):
    """QA could not produce a usable result. ``report`` is set when one was written."""

    def __init__(self, code: str, message: str, report: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.report = report


@dataclass
class QaResult:
    status: str
    report: Dict[str, Any]
    failed_checks: List[str] = field(default_factory=list)
    skipped_checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        """Short form kept in the project state (the full detail is in test_report.json)."""
        return {
            "status": self.status,
            "attempt": self.report["run"]["attempt"],
            "failed_checks": self.failed_checks,
            "skipped_checks": self.skipped_checks,
            "warnings": self.warnings,
        }


@contextmanager
def _qa_lock():
    with _thread_lock:
        handle = None
        if fcntl is not None:
            try:
                handle = open(_LOCK_FILE, "w")
                fcntl.flock(handle, fcntl.LOCK_EX)
            except OSError:
                handle = None
        try:
            yield
        finally:
            if handle is not None:
                try:
                    fcntl.flock(handle, fcntl.LOCK_UN)
                finally:
                    handle.close()


def run_qa_stage(workdir: Path, app_dir: Path, requirements_path: Path, runner: QaRunner) -> QaResult:
    """Run QA once (attempt 0) and return its outcome. Raises ``QaBlocked``."""
    workdir = Path(workdir)
    with _qa_lock():
        try:
            report = runner(app_dir, requirements_path, attempt=0)
        except subprocess.TimeoutExpired as exc:
            raise QaBlocked("qa_failed", f"QA did not finish within {int(exc.timeout)} seconds") from exc
        except Exception as exc:
            raise QaBlocked("qa_failed", f"QA could not run: {_first_line(exc, workdir)}") from exc
        if not isinstance(report, dict):
            raise QaBlocked("qa_failed", "QA returned no report")
        # Screenshots and traces sit in a folder the next run clears: copy them now.
        try:
            report = _localise(report, workdir)
        except Exception as exc:
            raise QaBlocked("qa_failed", f"QA report could not be stored: {_first_line(exc, workdir)}") from exc

    try:
        QAReport.model_validate(report)
    except Exception as exc:
        raise QaBlocked("qa_failed", "QA report does not match the agreed format") from exc
    return _classify(report)


def metrics_from_report(report: Dict[str, Any], run_time_seconds: float) -> Dict[str, Any]:
    """Project.metrics as the frontend reads it (frontend/README.md, "QA report -> metrics").

    ``run_time_seconds`` is the whole pipeline, measured by the orchestrator;
    the QA run alone is ``run.duration_ms`` in the report.
    """
    summary = report["summary"]
    return {
        "pass_rate": summary["pass_rate"],
        "checks_passed": summary["passed"],
        "checks_total": summary["total"],
        "checks_failed": summary["failed"],
        "checks_skipped": summary["skipped"],
        "checks_not_run": summary["not_run"],
        "run_time_seconds": round(run_time_seconds, 1),
    }


# ---------- internals ----------


def _classify(report: Dict[str, Any]) -> QaResult:
    summary, run = report["summary"], report["run"]
    by_status = lambda status: [c["id"] for c in report["checks"] if c["status"] == status]
    result = QaResult(
        status=QA_PASSED,
        report=report,
        failed_checks=by_status("failed"),
        skipped_checks=by_status("skipped"),
        warnings=list(report.get("warnings") or []),
    )
    if run.get("blocked_reason"):
        reason = str(run["blocked_reason"]).strip().splitlines()
        raise QaBlocked("qa_blocked", "QA cannot test this application: " + " ".join(reason)[:400], report)
    if summary["failed"] > 0:
        result.status = QA_FAILED
        return result
    # Nothing failed. It only counts as a pass if checks really ran and none was left out.
    if summary["not_run"] > 0 or summary["passed"] == 0:
        raise QaBlocked(
            "qa_blocked",
            f"QA did not run all checks: {summary['passed']} passed, {summary['not_run']} not run, "
            f"{summary['skipped']} skipped",
            report,
        )
    return result


def _localise(report: Dict[str, Any], workdir: Path) -> Dict[str, Any]:
    """Point the report at the project's own files and drop server paths."""
    repo_dir = Path(qa_runner.REPO_DIR)
    evidence_dir = workdir / EVIDENCE_DIRNAME
    if evidence_dir.exists():
        shutil.rmtree(evidence_dir)

    def keep(evidence: Any, check_id: str) -> None:
        if not isinstance(evidence, dict):
            return
        for kind in ("screenshot", "trace"):
            source = evidence.get(kind)
            if not source:
                continue
            source_path = (repo_dir / source).resolve()
            evidence[kind] = None
            if source_path.is_file():
                evidence_dir.mkdir(parents=True, exist_ok=True)
                target = evidence_dir / f"{check_id}-{kind}{source_path.suffix}"
                shutil.copyfile(source_path, target)
                evidence[kind] = f"{EVIDENCE_DIRNAME}/{target.name}"

    copied: Dict[str, Dict[str, Any]] = {}
    for check in report.get("checks") or []:
        keep(check.get("evidence"), check.get("id", "check"))
        copied[check.get("id")] = check.get("evidence")
    for defect in report.get("defects") or []:
        # Defects repeat the evidence of their check: reuse the copied paths.
        if defect.get("check_id") in copied and isinstance(copied[defect["check_id"]], dict):
            defect["evidence"] = dict(copied[defect["check_id"]])

    inputs = report.get("inputs")
    if isinstance(inputs, dict):
        inputs["requirements_path"] = "requirements.json"
        inputs["app_dir"] = "app"

    roots = sorted({str(workdir.resolve()), str(workdir), str(repo_dir)}, key=len, reverse=True)
    return _scrub(report, roots)


def _scrub(value: Any, roots: List[str]) -> Any:
    if isinstance(value, str):
        for root in roots:
            value = value.replace(root + "/", "").replace(root + "\\", "").replace(root, "")
        return value
    if isinstance(value, list):
        return [_scrub(item, roots) for item in value]
    if isinstance(value, dict):
        return {key: _scrub(item, roots) for key, item in value.items()}
    return value


def _first_line(exc: BaseException, workdir: Path) -> str:
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
    roots = sorted({str(Path(workdir).resolve()), str(workdir), str(qa_runner.REPO_DIR)}, key=len, reverse=True)
    return _scrub(text, roots)[:300]
