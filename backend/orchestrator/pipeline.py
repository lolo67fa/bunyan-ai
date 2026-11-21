"""MVP pipeline: approved requirements -> Architect -> Developer -> QA Tester -> Project Manager.

This module does not know about FastAPI or backend storage. The caller passes the
project dict, the folder to write into, and a callback that persists the project.

Repair loop (BUNYAN_REPAIR, default "restore"): when QA finds defects, the Developer repairs
the app and QA re-tests it in a real browser, at most MAX_REPAIRS times. Only a repair that really
changed a file is followed by a re-test and counted; the history is saved as repair_history.json.
The only strategy is deterministic ("restore_from_contracts", no LLM); see backend/agents/developer/repair.py.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.agents.architect import ArchitectureError, build_architecture
from backend.agents.developer import DeveloperError, generate
from backend.agents.developer.repair import MAX_REPAIRS, restore_from_contracts
from backend.agents.project_manager import OUTPUT_FILES, run_project_manager, write_outputs

PLAN_FILE, RISKS_FILE = OUTPUT_FILES
from backend.agents.qa_tester.runner import run_qa
from backend.orchestrator.qa_stage import (
    QA_BLOCKED,
    QA_NOT_RUN,
    TEST_REPORT_FILE,
    QaBlocked,
    QaRunner,
    metrics_from_report,
    run_qa_stage,
)

REPAIR_HISTORY_FILE = "repair_history.json"
INITIAL_REPORT_FILE = "test_report.initial.json"
REPAIR_ENV_VAR = "BUNYAN_REPAIR"  # "restore" (default), "llm" (authorised testers, see llm_repair.py) or "off"
RepairStrategy = Callable[[Dict[str, Any], Dict[str, Any], Path, List[Dict[str, Any]], int], Any]

REQUIREMENTS_FILE = "requirements.json"
ARCHITECTURE_FILE = "architecture.json"
APP_DIRNAME = "app"
APP_FILES = ("index.html", "style.css", "app.js")

# Set BUNYAN_QA=off to stop after the Developer (no Node.js or browser needed).
QA_ENV_VAR = "BUNYAN_QA"

# Placeholder the Developer template replaces with the architecture (templates/crud/app.js).
_TEMPLATE_PLACEHOLDER = "__BUNYAN_CONFIG__"
_REQUIRED_KEYS = ("schema_version", "status", "app", "entities")


class PipelineNotApproved(ValueError):
    """The pipeline was started for a project the user has not approved.

    This is a mistake in the caller, not a failed run, so the project is left untouched.
    """


class _StageFailure(Exception):
    """Internal: stops the run and carries the error the frontend will show."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def run_pipeline(
    project: dict,
    workdir: Path,
    on_update: Callable[[dict], None],
    *,
    qa_runner: Optional[QaRunner] = None,
    repair: Optional[RepairStrategy] = None,
) -> dict:
    """Run Architect, Developer and QA for one approved project and store the files.

    ``project`` is updated in place (existing fields are kept) and returned.
    ``on_update(project)`` is called after every state change so the caller can save it.

    Files written under ``workdir``::

        requirements.json
        architecture.json
        app/index.html
        app/style.css
        app/app.js
        test_report.json        (when QA ran)
        qa_evidence/            (screenshots and traces of failed checks)
        project_plan.md
        risks.md

    QA runs the existing QA Tester once (attempt 0). ``qa_runner`` replaces it in
    tests; by default it is ``run_qa``, unless the environment has ``BUNYAN_QA=off``,
    in which case the run stops after the Developer and ``project["qa"]["status"]``
    is ``"not_run"``.

    How a run ends:

    - ``completed`` with ``qa.status == "passed"``: no check failed.
    - ``completed`` with ``qa.status == "failed"``: the app was generated and QA found
      real defects. They are in ``test_report.json`` and in ``metrics``.
    - ``failed`` with ``error.code`` ``qa_blocked`` or ``qa_failed``: QA could not test
      the app. The generated files stay available.
    - ``failed`` with ``documentation_failed``: the Project Manager could not write its
      two documents. The generated app, the QA report and the metrics are kept.
    - ``failed`` with another code: Architect, Developer or storage problem.

    The Project Manager runs after QA, whatever QA concluded, and records the real
    result. It does not run when QA was blocked, because that run has already failed.

    The function does not raise for those. It raises ``PipelineNotApproved`` when
    ``requirements_approved`` is not ``True``.
    """
    if project.get("requirements_approved") is not True:
        raise PipelineNotApproved("Requirements must be approved by the user before the pipeline runs")

    started = time.monotonic()
    workdir = Path(workdir)
    app_dir = workdir / APP_DIRNAME
    project["error"] = None
    project["artifacts"] = []
    if qa_runner is None and _qa_enabled():
        qa_runner = run_qa
    if repair is None and _repair_enabled():
        repair = _default_repair(project)
    project["repair_attempt"] = 0
    project["repair"] = None

    try:
        requirements = _checked_requirements(project.get("requirements"))
        _write_json(workdir / REQUIREMENTS_FILE, requirements)

        _update(project, on_update, workdir, status="designing", current_agent="software_architect")
        architecture = _design(requirements)
        _write_json(workdir / ARCHITECTURE_FILE, architecture)

        _update(project, on_update, workdir, status="developing", current_agent="developer")
        _develop(requirements, architecture, app_dir)
        _check_outputs(workdir)

        qa_report = None
        if qa_runner is None:
            project["qa"] = {"status": QA_NOT_RUN, "reason": f"QA is switched off ({QA_ENV_VAR}=off)"}
        else:
            _update(project, on_update, workdir, status="testing", current_agent="qa_tester")
            qa_report = _test(project, workdir, app_dir, qa_runner, started)
            if repair is not None:
                qa_report = _repair_loop(project, on_update, workdir, app_dir, requirements, architecture,
                                         qa_runner, repair, qa_report, started)

        _update(project, on_update, workdir, status="documenting", current_agent="project_manager")
        _document(project, workdir, requirements, architecture, qa_report)

        _update(project, on_update, workdir, status="completed", current_agent=None)
    except _StageFailure as failure:
        project["error"] = {"code": failure.code, "message": failure.message}
        _update(project, on_update, workdir, status="failed")
    return project


# ---------- stages ----------


def _checked_requirements(requirements: Any) -> Dict[str, Any]:
    """Basic shape only. The Architect does the detailed MVP checks."""
    if not isinstance(requirements, dict):
        raise _StageFailure("invalid_requirements", "Project has no requirements document")
    missing = [key for key in _REQUIRED_KEYS if key not in requirements]
    if missing:
        raise _StageFailure("invalid_requirements", f"Requirements are missing: {', '.join(missing)}")
    if requirements["status"] != "ready_for_review":
        raise _StageFailure(
            "invalid_requirements",
            f"Requirements status is {requirements['status']!r}; expected 'ready_for_review'",
        )
    if not isinstance(requirements["entities"], list) or not isinstance(requirements["app"], dict):
        raise _StageFailure("invalid_requirements", "Requirements 'entities' must be a list and 'app' an object")
    return requirements


def _design(requirements: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return build_architecture(requirements)
    except ArchitectureError as exc:
        raise _StageFailure("architecture_unsupported", "; ".join(exc.reasons)) from exc
    except Exception as exc:  # malformed requirements can break the Architect in other ways
        raise _StageFailure("architecture_failed", f"Architect failed: {_describe(exc)}") from exc


def _develop(requirements: Dict[str, Any], architecture: Dict[str, Any], app_dir: Path) -> None:
    try:
        generate(requirements, architecture, app_dir)
    except DeveloperError as exc:
        raise _StageFailure("generation_failed", str(exc)) from exc
    except OSError as exc:
        raise _StageFailure("storage_failed", f"Could not write the application files: {_describe(exc)}") from exc
    except Exception as exc:
        raise _StageFailure("generation_failed", f"Developer failed: {_describe(exc)}") from exc


def _test(project: dict, workdir: Path, app_dir: Path, qa_runner: QaRunner, started: float,
          attempt: int = 0) -> Dict[str, Any]:
    """Run QA, store its report and put the real numbers on the project. Returns the report."""
    try:
        result = run_qa_stage(workdir, app_dir, workdir / REQUIREMENTS_FILE, qa_runner, workdir / ARCHITECTURE_FILE,
                              attempt=attempt)
    except QaBlocked as blocked:
        project["qa"] = {"status": QA_BLOCKED, "reason": blocked.message}
        if blocked.report is not None:
            _write_json(workdir / TEST_REPORT_FILE, blocked.report)
            project["metrics"] = metrics_from_report(blocked.report, time.monotonic() - started)
        raise _StageFailure(blocked.code, blocked.message) from blocked

    _write_json(workdir / TEST_REPORT_FILE, result.report)
    project["qa"] = result.summary()
    project["metrics"] = metrics_from_report(result.report, time.monotonic() - started)
    return result.report


def _document(
    project: dict,
    workdir: Path,
    requirements: Dict[str, Any],
    architecture: Dict[str, Any],
    qa_report: Optional[Dict[str, Any]],
) -> None:
    """Project Manager: write project_plan.md and risks.md from this run's real data."""
    sizes = {}
    for rel in _expected_files() + [TEST_REPORT_FILE]:
        if _is_real_file(workdir / rel):
            sizes[Path(rel).name] = (workdir / rel).stat().st_size
    try:
        result = run_project_manager(
            {
                "project_id": project.get("project_id"),
                "status": "documenting",
                "requirements": requirements,
                "architecture": architecture,
                "test_report": qa_report,
                "qa": project.get("qa"),
                "generated_files": [name for name in APP_FILES if _is_real_file(workdir / APP_DIRNAME / name)],
                "repair_attempt": project.get("repair_attempt") or 0,
                # True only when this run really had a repair loop (QA ran and BUNYAN_REPAIR is on)
                "repair_loop_available": bool(project.get("repair")),
                "repair_history": project.get("repair"),
                "run_time_seconds": (project.get("metrics") or {}).get("run_time_seconds"),
            },
            mode="rules",  # the pipeline never makes a paid call for the documents
        )
        write_outputs(result, workdir)
    except OSError as exc:
        raise _StageFailure("documentation_failed", f"Could not write the project documents: {_describe(exc)}") from exc
    except Exception as exc:
        raise _StageFailure("documentation_failed", f"Project Manager failed: {_describe(exc)}") from exc
    missing = [name for name in (PLAN_FILE, RISKS_FILE) if not _is_real_file(workdir / name)]
    if missing:
        raise _StageFailure("documentation_failed", f"Project documents are missing or empty: {', '.join(missing)}")


def _repair_loop(project, on_update, workdir, app_dir, requirements, architecture, qa_runner, repair,
                 report, started) -> Dict[str, Any]:
    """Developer -> QA re-test, at most MAX_REPAIRS times. Returns the last real QA report.

    Stops when QA passes, when the repair changed nothing (no re-test, nothing claimed), when the
    repair output is invalid, or when the budget is used. QA blocked on a re-test fails the run as usual.
    """
    first = project["qa"]
    history: List[Dict[str, Any]] = [{"attempt": 0, "step": "test", "qa": _qa_entry(report, first)}]
    state = {"available": True, "max_repairs": MAX_REPAIRS, "strategy": getattr(repair, "__name__", "custom"),
             "history": history, "stopped": None}
    project["repair"] = state

    def save():
        _write_json(workdir / REPAIR_HISTORY_FILE, state)

    save()
    if first["status"] != "failed":
        state["stopped"] = "passed"
        save()
        return report
    _write_json(workdir / INITIAL_REPORT_FILE, report)  # the original failure report is never overwritten
    for attempt in range(1, MAX_REPAIRS + 1):
        _update(project, on_update, workdir, status="repairing", current_agent="developer")
        defects = [d for d in (report.get("defects") or []) if isinstance(d, dict)]
        if not defects:
            defects = [{"check_id": c, "message": "failed"} for c in project["qa"].get("failed_checks", [])]
        try:
            change = repair(requirements, architecture, app_dir, defects, attempt)
            changed = list(change.changed_files)
            _check_outputs(workdir)
        except _StageFailure as bad:
            history.append({"attempt": attempt, "step": "repair", "result": "invalid_output", "reason": bad.message})
            state["stopped"] = "invalid_repair_output"
            break
        except Exception as exc:  # RepairRejected / RepairUnavailable carry their own stop reason
            stop = getattr(exc, "stop_reason", "repair_error")
            history.append({"attempt": attempt, "step": "repair", "result": "rejected" if stop == "invalid_repair_output"
                            else "unavailable" if stop == "repair_unavailable" else "error", "reason": _describe(exc)})
            state["stopped"] = stop
            break
        entry = {"attempt": attempt, "step": "repair", "strategy": change.strategy, "defects": change.defects,
                 "changed_files": changed, "result": "changed" if changed else "no_change"}
        details = getattr(change, "details", None)
        if details:
            entry.update(details)  # AI repair: diagnosis, the diff that was applied, number of edits
        history.append(entry)
        if not changed:
            state["stopped"] = "no_change"  # nothing to re-test, and no repair is claimed
            break
        project["repair_attempt"] = attempt
        _update(project, on_update, workdir, status="testing", current_agent="qa_tester")
        try:
            report = _test(project, workdir, app_dir, qa_runner, started, attempt=attempt)
        except _StageFailure:
            history.append({"attempt": attempt, "step": "test", "qa": {"status": "blocked", "reason": project["qa"].get("reason")}})
            state["stopped"] = "qa_blocked"
            save()
            raise
        history.append({"attempt": attempt, "step": "test", "qa": _qa_entry(report, project["qa"])})
        save()
        if project["qa"]["status"] != "failed":
            state["stopped"] = "passed"
            break
    else:
        state["stopped"] = "budget_used"
    save()
    return report


def _qa_entry(report: Dict[str, Any], qa: Dict[str, Any]) -> Dict[str, Any]:
    failed = [{"check_id": c["id"], "message": ((c.get("error") or {}).get("message") or "").splitlines()[0][:300]
               if (c.get("error") or {}).get("message") else ""}
              for c in report.get("checks", []) if c.get("status") == "failed"]
    s = report["summary"]
    return {"status": qa["status"], "passed": s["passed"], "total": s["total"], "failed": failed}


def _repair_mode() -> str:
    mode = os.environ.get(REPAIR_ENV_VAR, "restore").strip().lower()
    return "off" if mode in ("off", "0", "false", "no") else mode


def _repair_enabled() -> bool:
    return _repair_mode() != "off"


def _default_repair(project: dict) -> RepairStrategy:
    """restore (default) for everyone; with BUNYAN_REPAIR=llm, restore first and then an AI repair,
    which runs only for an owner who unlocked the protected real analyst (checked at repair time)."""
    if _repair_mode() == "llm":
        from backend.agents.developer.llm_repair import make_llm_repair

        return make_llm_repair(project.get("owner"))
    return restore_from_contracts


def _qa_enabled() -> bool:
    return os.environ.get(QA_ENV_VAR, "on").strip().lower() not in ("off", "0", "false", "no")


def _check_outputs(workdir: Path) -> None:
    """A run is complete only if every expected file is really there."""
    missing = [rel for rel in _expected_files() if not _is_real_file(workdir / rel)]
    if missing:
        raise _StageFailure("generation_failed", f"Generated files are missing or empty: {', '.join(missing)}")
    try:
        script = (workdir / APP_DIRNAME / "app.js").read_text(encoding="utf-8")
    except OSError as exc:
        raise _StageFailure("storage_failed", f"Could not read app.js: {_describe(exc)}") from exc
    if _TEMPLATE_PLACEHOLDER in script:
        raise _StageFailure("generation_failed", "app.js still contains the template placeholder")


# ---------- helpers ----------


def _expected_files() -> List[str]:
    return [REQUIREMENTS_FILE, ARCHITECTURE_FILE] + [f"{APP_DIRNAME}/{name}" for name in APP_FILES]


def _is_real_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _artifacts(workdir: Path) -> List[Dict[str, Any]]:
    """Files that exist right now, in the shape the frontend reads: {"name", "available"}."""
    found = []
    for rel in _expected_files() + [TEST_REPORT_FILE, PLAN_FILE, RISKS_FILE, REPAIR_HISTORY_FILE, INITIAL_REPORT_FILE]:
        if _is_real_file(workdir / rel):
            found.append({"name": Path(rel).name, "available": True, "path": rel})
    return found


def _update(project: dict, on_update: Callable[[dict], None], workdir: Path, status: str, **fields: Optional[str]) -> None:
    project["status"] = status
    project.update(fields)
    project["artifacts"] = _artifacts(workdir)
    on_update(project)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, TypeError, ValueError) as exc:
        raise _StageFailure("storage_failed", f"Could not write {path.name}: {_describe(exc)}") from exc


def _describe(exc: BaseException) -> str:
    """Short reason for the user. OS errors are reduced to their reason text
    because their full message contains absolute paths on the server."""
    if isinstance(exc, OSError) and exc.strerror:
        return f"{type(exc).__name__}: {exc.strerror}"
    return f"{type(exc).__name__}: {exc}"
