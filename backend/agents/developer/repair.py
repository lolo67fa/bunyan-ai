"""QA repair coordination. QA executes the actual browser tests; this module never fakes passes."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any

MAX_REPAIRS = 2

@dataclass
class RepairOutcome:
    report: dict
    attempts: int
    history: list[dict]

def run_with_repairs(initial_generate: Callable[[], Any], run_qa: Callable[[int], dict],
                     repair: Callable[[list[dict], int], Any]) -> RepairOutcome:
    """Caller supplies code repair strategy; QA report drives at most two fixes.

    run_qa(attempt) must execute real Playwright and return Sara's report contract.
    repair(defects, attempt) must change code and may use an LLM; no silent fallback.
    """
    initial_generate()
    history=[]
    for attempt in range(MAX_REPAIRS + 1):
        report=run_qa(attempt)
        if not isinstance(report,dict) or 'summary' not in report or 'run' not in report:
            raise ValueError('Invalid QA report')
        if report['run'].get('attempt') != attempt:
            raise ValueError('QA attempt does not match expected attempt')
        history.append(report)
        if report['summary'].get('all_passed') is True and report['summary'].get('passed')==8 and report['summary'].get('total')==8:
            return RepairOutcome(report,attempt,history)
        defects=report.get('defects') or []
        if attempt==MAX_REPAIRS or not defects:
            return RepairOutcome(report,attempt,history)
        for defect in defects:
            if not isinstance(defect.get('check_id'),str) or not isinstance(defect.get('message'),str):
                raise ValueError('Malformed defect in QA report')
        repair(defects,attempt+1)
    raise AssertionError('Unreachable')


# ---------- the repair strategy the pipeline uses ----------

import hashlib
import tempfile
from pathlib import Path

from .generator import generate

APP_FILES = ("index.html", "style.css", "app.js")
STRATEGY_RESTORE = "restore_from_contracts"


@dataclass
class RepairChange:
    """What one repair attempt did to the generated app. ``changed_files`` is empty when it changed nothing."""

    attempt: int
    strategy: str
    defects: list[dict]
    changed_files: list[dict]

    @property
    def changed(self) -> bool:
        return bool(self.changed_files)

    def as_dict(self) -> dict:
        return {"attempt": self.attempt, "strategy": self.strategy, "defects": self.defects,
                "changed_files": self.changed_files}


def _sha(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest()[:16] if data is not None else None


def restore_from_contracts(requirements: dict, architecture: dict, app_dir: str | Path,
                           defects: list[dict], attempt: int) -> RepairChange:
    """Deterministic repair (no LLM, no cost): rebuild the app the approved contracts describe and
    replace every generated file that differs from it (damaged, edited, stale or missing).

    The QA defects say which checks failed; this strategy cannot invent new code, so when the files
    already match the contracts it changes nothing and reports that (the caller then stops: no
    retest, no repair claimed). ``changed_files`` lists each replaced file with its hash before and after.
    """
    for d in defects:
        if not isinstance(d, dict) or not isinstance(d.get("check_id"), str) or not isinstance(d.get("message"), str):
            raise ValueError("Malformed defect in QA report")
    app_dir = Path(app_dir)
    changed = []
    with tempfile.TemporaryDirectory(prefix="bunyan-repair-") as tmp:
        generate(requirements, architecture, tmp)
        for name in APP_FILES:
            expected = (Path(tmp) / name).read_bytes()
            target = app_dir / name
            current = target.read_bytes() if target.is_file() else None
            if current != expected:
                target.write_bytes(expected)
                changed.append({"file": name, "before": _sha(current), "after": _sha(expected),
                                "reason": "missing" if current is None else "differed from the approved contracts"})
    return RepairChange(attempt, STRATEGY_RESTORE,
                        [{"check_id": d["check_id"], "message": d["message"].splitlines()[0][:300]} for d in defects],
                        changed)
