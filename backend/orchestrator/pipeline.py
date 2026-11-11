"""MVP pipeline: approved requirements -> Architect -> Developer -> stored CRUD app files.

This module does not know about FastAPI or backend storage. The caller passes the
project dict, the folder to write into, and a callback that persists the project.

Not included yet: QA, the repair loop, the Project Manager agent, preview and download.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.agents.architect import ArchitectureError, build_architecture
from backend.agents.developer import DeveloperError, generate

REQUIREMENTS_FILE = "requirements.json"
ARCHITECTURE_FILE = "architecture.json"
APP_DIRNAME = "app"
APP_FILES = ("index.html", "style.css", "app.js")

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


def run_pipeline(project: dict, workdir: Path, on_update: Callable[[dict], None]) -> dict:
    """Run Architect then Developer for one approved project and store the files.

    ``project`` is updated in place (existing fields are kept) and returned.
    ``on_update(project)`` is called after every state change so the caller can save it.

    Files written under ``workdir``::

        requirements.json
        architecture.json
        app/index.html
        app/style.css
        app/app.js

    The final status is ``completed`` only when all five files exist. Any problem ends
    with ``status="failed"`` and ``error={"code", "message"}``; the function does not
    raise for those. It raises ``PipelineNotApproved`` when ``requirements_approved``
    is not ``True``.
    """
    if project.get("requirements_approved") is not True:
        raise PipelineNotApproved("Requirements must be approved by the user before the pipeline runs")

    workdir = Path(workdir)
    app_dir = workdir / APP_DIRNAME
    project["error"] = None
    project["artifacts"] = []

    try:
        requirements = _checked_requirements(project.get("requirements"))
        _write_json(workdir / REQUIREMENTS_FILE, requirements)

        _update(project, on_update, workdir, status="designing", current_agent="software_architect")
        architecture = _design(requirements)
        _write_json(workdir / ARCHITECTURE_FILE, architecture)

        _update(project, on_update, workdir, status="developing", current_agent="developer")
        _develop(requirements, architecture, app_dir)
        _check_outputs(workdir)

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
    for rel in _expected_files():
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
