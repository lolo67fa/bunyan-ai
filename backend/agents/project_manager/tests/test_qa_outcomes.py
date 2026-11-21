"""The four reporting rules the pipeline relies on (no LLM, rules mode).

1. No text claims or promises a repair unless the run has a repair loop.
2. The QA error message of a failed check reaches risks.md.
3. passed, failed, blocked, not_run and skipped are told apart.
4. A run time of 0 seconds is shown, not hidden.
"""

import copy

from backend.agents.project_manager import run_project_manager

from .conftest import load_input


def stage(result, key):
    return next(s for s in result.stages if s.key == key)


def failing_run(**changes):
    """The failing-check sample as the current pipeline sends it: no repair loop, no repairs."""
    data = copy.deepcopy(load_input("appointment_tests_failing_en"))
    data.update(repair_attempt=0, repair_loop_available=False)
    data["test_report"]["run"]["attempt"] = 0
    data.update(changes)
    return data


def test_no_repair_is_claimed_without_a_repair_loop():
    result = run_project_manager(failing_run())
    text = (result.project_plan_md + result.risks_md + result.summary).lower()
    for claim in ("went back to the developer", "repair attempts are used", "after 1 repair", "after 2 repairs",
                  "fixed it in attempt"):
        assert claim not in text, claim
    assert "**automatic repair:** not available in this version" in result.project_plan_md.lower()
    assert stage(result, "tests").status == "failed"  # no repair is coming: the stage ended with a defect
    assert "no automatic repair in this version" in result.risks[0].mitigation.lower()


def test_a_completed_run_with_qa_attempt_one_but_no_loop_claims_no_fix():
    data = copy.deepcopy(load_input("inventory_dialect_ar"))
    data["repair_loop_available"] = False
    result = run_project_manager(data)
    assert not any(r.status == "closed" and r.source == "test_report.run.attempt" for r in result.risks)
    assert "إصلاح" not in result.summary


def test_the_failed_check_keeps_the_real_qa_message():
    data = failing_run()
    message = data["test_report"]["checks"][4]["error"]["message"]
    assert data["test_report"]["checks"][4]["status"] == "failed" and message
    result = run_project_manager(data)
    first_line = message.strip().splitlines()[0][:200]
    assert first_line in result.risks[0].title and first_line in result.risks_md


def test_qa_switched_off_is_not_run_and_not_a_stopped_build():
    data = copy.deepcopy(load_input("task_manager_en"))
    data.pop("test_report", None)
    data["qa"] = {"status": "not_run", "reason": "QA is switched off (BUNYAN_QA=off)"}
    result = run_project_manager(data)
    assert stage(result, "tests").status == "not_started" and "Not run" in stage(result, "tests").output
    assert "complete but was not tested" in result.summary and "stopped at" not in result.summary
    assert "The app was not tested (QA is switched off" in result.risks_md
    assert "- **Tests:** not run (QA is switched off (BUNYAN_QA=off))." in result.project_plan_md


def test_blocked_qa_is_a_failed_stage_with_its_reason():
    data = copy.deepcopy(load_input("task_manager_en"))
    data["test_report"]["run"]["blocked_reason"] = "Chromium could not start"
    for c in data["test_report"]["checks"]:
        c["status"] = "not_run"
    data["test_report"]["summary"].update(passed=0, not_run=8, all_passed=False, pass_rate=0)
    result = run_project_manager(data)
    assert stage(result, "tests").status == "failed"
    assert "Tests could not run: Chromium could not start" in result.risks_md


def test_skipped_and_not_run_checks_are_reported_separately():
    data = copy.deepcopy(load_input("task_manager_en"))
    data["test_report"]["summary"].update(skipped=2, not_run=1)
    result = run_project_manager(data)
    titles = [r.title for r in result.risks]
    assert "2 checks did not apply to this app" in titles
    assert "1 checks did not run" in titles


def test_zero_run_time_is_shown():
    data = copy.deepcopy(load_input("task_manager_en"))
    data["run_time_seconds"] = 0
    result = run_project_manager(data)
    assert "| **Total** |" in result.project_plan_md and "within the 90 s target" in result.project_plan_md
