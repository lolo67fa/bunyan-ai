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
