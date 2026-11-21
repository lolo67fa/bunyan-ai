"""The repair loop: Developer -> QA -> Developer repair -> QA re-test, at most two repairs.

Offline tests use a stand-in QA runner (scripted reports in Sara's format) and damage the
generated app the way a real defect would, so the deterministic repair has something real to
change. The real tests (``needs_playwright``) run Sara's Playwright suite in Chromium.
"""

import copy
import json
from pathlib import Path

import pytest

from backend.agents.developer import repair as repair_module
from backend.orchestrator import pipeline, run_pipeline

from test_qa_pipeline import (Recorder, load_requirements, make_project, needs_playwright,
                               report_in_saras_format)

BREAK = "localStorage.clear();\n"  # forgets every record: persist_after_refresh fails for real


@pytest.fixture(autouse=True)
def repair_on(monkeypatch):
    monkeypatch.setenv("BUNYAN_REPAIR", "restore")


def damage(app_dir):
    script = Path(app_dir) / "app.js"
    script.write_text(BREAK + script.read_text(encoding="utf-8"), encoding="utf-8")


class ScriptedQa:
    """Attempt n returns outcomes[n]: "pass" or "fail". ``damage_until`` re-breaks the app before
    returning a failure on attempts below it, like a defect the repair did not fully remove."""

    def __init__(self, *outcomes, damage_until=0, blocked_on=None):
        self.outcomes, self.damage_until, self.blocked_on = outcomes, damage_until, blocked_on
        self.calls = []

    def __call__(self, app_dir, requirements_path, attempt=0, app_path="/", architecture_path=None):
        self.calls.append(attempt)
        script = (Path(app_dir) / "app.js").read_text(encoding="utf-8")
        self.seen_broken = script.startswith(BREAK)
        if attempt < self.damage_until and not script.startswith(BREAK):
            damage(app_dir)
        if self.blocked_on == attempt:
            report = report_in_saras_format(blocked_reason="Chromium could not start")
        elif self.outcomes[attempt] == "fail":
            report = report_in_saras_format({"persist_after_refresh": "failed"})
            report["checks"][4]["error"]["message"] = "record is missing after reload"
            report["defects"][0]["message"] = "record is missing after reload"
        else:
            report = report_in_saras_format()
        report["run"]["attempt"] = attempt
        return report


def run(tmp_path, qa, requirements="task_manager_en", repair=None, broken=True):
    if broken:
        real_generate = pipeline.generate

        def generate_broken(req, arch, out):
            files = real_generate(req, arch, out)
            damage(out)
            return files

        pipeline.generate = generate_broken
    try:
        project = run_pipeline(make_project(load_requirements(requirements)), tmp_path, Recorder(),
                               qa_runner=qa, **({"repair": repair} if repair else {}))
    finally:
        if broken:
            pipeline.generate = real_generate
    history = json.loads((tmp_path / "repair_history.json").read_text(encoding="utf-8"))
    return project, history, (tmp_path / "project_plan.md").read_text(encoding="utf-8"), \
        (tmp_path / "risks.md").read_text(encoding="utf-8")


def steps(history, kind):
    return [h for h in history["history"] if h["step"] == kind]


def test_initial_pass_needs_no_repair(tmp_path):
    qa = ScriptedQa("pass")
    project, history, plan, _ = run(tmp_path, qa, broken=False)
    assert qa.calls == [0] and project["repair_attempt"] == 0 and history["stopped"] == "passed"
    assert not (tmp_path / "test_report.initial.json").exists()
    assert "- **Repair attempts:** 0 of 2." in plan and "repair" not in project["qa"].get("reason", "")


def test_one_repair_really_changes_the_app_and_the_retest_passes(tmp_path):
    qa = ScriptedQa("fail", "pass")
    project, history, plan, risks = run(tmp_path, qa)
    assert qa.calls == [0, 1]
    assert not (tmp_path / "app" / "app.js").read_text(encoding="utf-8").startswith(BREAK)  # really repaired
    [fix] = steps(history, "repair")
    assert fix["result"] == "changed" and fix["changed_files"][0]["file"] == "app.js"
    assert fix["changed_files"][0]["before"] != fix["changed_files"][0]["after"]
    assert fix["defects"] == [{"check_id": "persist_after_refresh", "message": "record is missing after reload"}]
    assert project["status"] == "completed" and project["qa"]["status"] == "passed" and project["repair_attempt"] == 1
    assert history["stopped"] == "passed" and [t["qa"]["status"] for t in steps(history, "test")] == ["failed", "passed"]
    initial = json.loads((tmp_path / "test_report.initial.json").read_text(encoding="utf-8"))
    assert initial["summary"]["failed"] == 1 and initial["run"]["attempt"] == 0  # the original failure is kept
    assert "after 1 repair" in plan and "Attempt 1: the Developer changed app.js" in plan
    assert "the Developer fixed it in attempt 1 of 2" in risks


def test_two_repairs_then_pass(tmp_path):
    qa = ScriptedQa("fail", "fail", "pass", damage_until=2)
    project, history, plan, _ = run(tmp_path, qa)
    assert qa.calls == [0, 1, 2] and project["repair_attempt"] == 2 and project["qa"]["status"] == "passed"
    assert [s["result"] for s in steps(history, "repair")] == ["changed", "changed"]
    assert "after 2 repairs" in plan


def test_two_repairs_fail_and_the_loop_stops(tmp_path):
    qa = ScriptedQa("fail", "fail", "fail", damage_until=3)
    project, history, plan, risks = run(tmp_path, qa)
    assert qa.calls == [0, 1, 2]  # never a third repair
    assert project["status"] == "completed" and project["qa"]["status"] == "failed" and project["repair_attempt"] == 2
    assert history["stopped"] == "budget_used"
    assert "Both repair attempts are used" in risks and "record is missing after reload" in risks


def test_a_repair_that_changes_nothing_is_not_claimed_and_not_retested(tmp_path):
    qa = ScriptedQa("fail")
    project, history, plan, risks = run(tmp_path, qa, broken=False)  # the files already match the contracts
    assert qa.calls == [0]
    assert project["repair_attempt"] == 0 and project["qa"]["status"] == "failed" and history["stopped"] == "no_change"
    assert steps(history, "repair")[0]["result"] == "no_change"
    assert "after 1 repair" not in plan and "fixed it" not in risks
    assert "found nothing to change" in risks and "Attempt 1: no file changed" in plan


def test_qa_blocked_on_the_retest_fails_the_run_honestly(tmp_path):
    qa = ScriptedQa("fail", "pass", blocked_on=1)
    project, history, _, _ = (None, None, None, None)
    project = run_pipeline(make_project(load_requirements("task_manager_en")), tmp_path, Recorder(), qa_runner=qa,
                           repair=lambda *a: _damaging_then_restore(*a))
    history = json.loads((tmp_path / "repair_history.json").read_text(encoding="utf-8"))
    assert project["status"] == "failed" and project["qa"]["status"] == "blocked" and history["stopped"] == "qa_blocked"
    assert (tmp_path / "app" / "index.html").exists()  # the app is kept


def _damaging_then_restore(req, arch, app_dir, defects, attempt):
    damage(app_dir)
    return repair_module.restore_from_contracts(req, arch, app_dir, defects, attempt)


def test_invalid_repair_output_stops_without_a_retest(tmp_path):
    def broken_repair(req, arch, app_dir, defects, attempt):
        (Path(app_dir) / "app.js").write_text("", encoding="utf-8")  # empty file: not a valid app
        return repair_module.RepairChange(attempt, "test", defects, [{"file": "app.js", "before": "x", "after": None}])

    qa = ScriptedQa("fail")
    project, history, _, risks = run(tmp_path, qa, repair=broken_repair)
    assert qa.calls == [0] and history["stopped"] == "invalid_repair_output"
    assert project["repair_attempt"] == 0 and "fixed it" not in risks


def test_malformed_defects_are_refused(tmp_path):
    # A QA report with malformed defects fails Sara's schema: the run stops as blocked, nothing is repaired.
    class BadDefects(ScriptedQa):
        def __call__(self, *a, **k):
            report = super().__call__(*a, **k)
            report["defects"] = [{"check_id": 5}]
            return report

    qa = BadDefects("fail")
    project = run_pipeline(make_project(load_requirements("task_manager_en")), tmp_path, Recorder(), qa_runner=qa)
    assert qa.calls == [0] and project["status"] == "failed" and project["repair_attempt"] == 0
    # The repair strategy refuses them too, and a strategy error stops the loop without a re-test.
    with pytest.raises(ValueError, match="Malformed defect"):
        repair_module.restore_from_contracts({}, {}, tmp_path, [{"check_id": 5}], 1)

    def failing_repair(*args):
        raise RuntimeError("the strategy crashed")

    qa = ScriptedQa("fail")
    project, history, _, _ = run(tmp_path / "second", qa, repair=failing_repair)
    assert qa.calls == [0] and history["stopped"] == "repair_error" and project["repair_attempt"] == 0


def test_arabic_project_one_repair(tmp_path):
    qa = ScriptedQa("fail", "pass")
    project, history, plan, risks = run(tmp_path, qa, requirements="scenario_b_inventory_ar")
    assert project["qa"]["status"] == "passed" and project["repair_attempt"] == 1
    assert "المحاولة 1: غيّر المطوّر app.js" in plan and "أصلحه المطوّر في المحاولة 1 من 2" in risks


def test_repair_can_be_switched_off(tmp_path, monkeypatch):
    monkeypatch.setenv("BUNYAN_REPAIR", "off")
    project = run_pipeline(make_project(load_requirements("task_manager_en")), tmp_path, Recorder(),
                           qa_runner=ScriptedQa("fail"))
    assert project["repair"] is None and not (tmp_path / "repair_history.json").exists()
    assert "Automatic repair:** not available" in (tmp_path / "project_plan.md").read_text(encoding="utf-8")


def test_the_new_files_are_served_and_zipped(tmp_path):
    from backend import artifacts
    assert {"repair_history.json", "test_report.initial.json"} <= set(artifacts.ARTIFACT_PATHS)


# ---------- real Playwright ----------

@needs_playwright
@pytest.mark.parametrize("name", ["task_manager_en", "scenario_b_inventory_ar"])
def test_real_qa_catches_the_defect_and_passes_after_the_repair(tmp_path, monkeypatch, qa_on, name):
    real_generate = pipeline.generate

    def generate_app_that_forgets(req, arch, out):
        files = real_generate(req, arch, out)
        damage(out)
        return files

    monkeypatch.setattr(pipeline, "generate", generate_app_that_forgets)
    project = run_pipeline(make_project(load_requirements(name)), tmp_path, Recorder())
    history = json.loads((tmp_path / "repair_history.json").read_text(encoding="utf-8"))
    tests = steps(history, "test")
    assert tests[0]["qa"]["status"] == "failed"
    assert [f["check_id"] for f in tests[0]["qa"]["failed"]] == ["persist_after_refresh"]  # found by real Chromium
    assert tests[1]["qa"] == {"status": "passed", "passed": 8, "total": 8, "failed": []}  # real re-test
    assert project["qa"]["status"] == "passed" and project["repair_attempt"] == 1 and project["status"] == "completed"
    final = json.loads((tmp_path / "test_report.json").read_text(encoding="utf-8"))
    assert final["run"]["attempt"] == 1 and final["summary"]["passed"] == 8
