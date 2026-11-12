"""Project Manager Agent: documents must repeat the run's real data and nothing else.

Requirements are the Business Analyst's sample outputs; architectures come from
the real Architect. QA reports are built in Sara's format (schema-checked).
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.agents.architect import build_architecture
from backend.agents.project_manager import (
    PLAN_FILE,
    RISKS_FILE,
    ProjectManagerError,
    build_documents,
    write_documents,
)
from backend.agents.qa_tester.schema import QAReport

SAMPLES = Path(__file__).resolve().parents[2] / "business_analyst" / "samples" / "outputs"
NOW = datetime(2026, 11, 12, 9, 30, 0, tzinfo=timezone.utc)
CHECK_IDS = [
    "create_item", "list_items", "edit_item", "delete_item",
    "persist_after_refresh", "reject_incomplete_input", "empty_state", "error_message_visible",
]
FILES = {"requirements.json": 11761, "architecture.json": 6136, "index.html": 1183, "style.css": 1933, "app.js": 13823}


def requirements(name):
    return json.loads((SAMPLES / f"{name}.requirements.json").read_text(encoding="utf-8"))


def qa_report(statuses=None, warnings=(), blocked_reason=None):
    statuses = statuses or {}
    checks = []
    for check_id in CHECK_IDS:
        status = statuses.get(check_id, "passed")
        checks.append({
            "id": check_id, "description": f"{check_id} description", "status": status,
            "duration_ms": 200 if status in ("passed", "failed") else 0, "related_criteria": [],
            "error": {"message": f"Expected 1 row, received 0 ({check_id})\nCall log: ..."} if status == "failed" else None,
            "skip_reason": "No required field can be left empty" if status == "skipped" else None,
            "evidence": {"screenshot": f"qa_evidence/{check_id}-screenshot.png" if status == "failed" else None, "trace": None},
        })
    count = lambda s: sum(1 for c in checks if c["status"] == s)
    report = {
        "schema_version": "0.1.0-proposal", "entity": "Task",
        "run": {"attempt": 0, "max_repair_attempts": 2, "started_at": "2026-11-12T09:29:55.000Z",
                "finished_at": "2026-11-12T09:29:58.000Z", "duration_ms": 3000, "browser": "chromium",
                "blocked_reason": blocked_reason},
        "summary": {"total": 8, "passed": count("passed"), "failed": count("failed"), "skipped": count("skipped"),
                    "not_run": count("not_run"), "pass_rate": count("passed") / 8, "all_passed": count("passed") == 8},
        "checks": checks,
        "defects": [{"check_id": c["id"], "message": c["error"]["message"], "evidence": c["evidence"]} for c in checks if c["status"] == "failed"],
        "warnings": list(warnings),
    }
    QAReport.model_validate(report)
    return report


def run_state(status="passed", **extra):
    state = {"repair_attempt": 0, "created_at": "2026-11-12T09:29:00+00:00",
             "metrics": {"pass_rate": 1, "checks_passed": 8, "checks_total": 8, "run_time_seconds": 3.2},
             "qa": {"status": status}}
    state.update(extra)
    return state


def documents(name="task_manager_en", report="default", run="default", files=FILES):
    req = requirements(name)
    report = qa_report() if report == "default" else report
    run = run_state() if run == "default" else run
    return build_documents(req, build_architecture(req), report, run, files, NOW), req


def table_rows(markdown):
    return [line for line in markdown.splitlines() if re.match(r"\| R-\d+ \|", line)]


# ---------- English, QA passed ----------


def test_english_plan_repeats_the_real_requirements():
    docs, req = documents()
    plan = docs[PLAN_FILE]

    assert plan.startswith("# Project plan — Task Manager\n")
    assert f"- Description: {req['app']['description']}" in plan
    assert "- Entity: Task (`Task`)" in plan
    assert f"- Fields: {len(req['entities'][0]['fields'])}" in plan
    must = sum(1 for r in req["functional_requirements"] if r["priority"] == "must")
    assert f"- Functional requirements: {len(req['functional_requirements'])} ({must} must-have)" in plan
    assert f"- User stories: {len(req['user_stories'])}" in plan
    assert f"- Acceptance criteria: {len(req['acceptance_criteria'])}" in plan
    for requirement in req["functional_requirements"]:
        assert f"| {requirement['id']} | {requirement['priority']} |" in plan
    for assumption in req["assumptions"]:
        assert f"- {assumption}" in plan


def test_plan_reports_the_real_qa_numbers_and_times():
    plan = documents()[0][PLAN_FILE]

    assert "- Test result: Passed: 8 of 8 checks passed" in plan
    assert "| Testing | test_report.json | Passed: 8 of 8 checks passed |" in plan
    assert "- Run time: 3.2 seconds" in plan
    assert "- Repair attempts: 0 of 2 (no automatic repair exists in this version)" in plan
    assert "| Project created | 2026-11-12T09:29:00+00:00 |" in plan
    assert "| Testing started | 2026-11-12T09:29:55.000Z |" in plan
    assert "| Documentation written | 2026-11-12 09:30:00 UTC |" in plan


def test_plan_lists_the_generated_files_with_their_sizes():
    plan = documents()[0][PLAN_FILE]
    for name, size in FILES.items():
        assert f"| `{name}` | {size} bytes |" in plan


def test_plan_says_what_is_not_available_instead_of_inventing_it():
    plan = documents()[0][PLAN_FILE]

    assert "## Not available" in plan
    assert "Schedule, deadlines and effort estimates" in plan
    assert "Cost and budget: not recorded." in plan
    assert "no people were assigned" in plan
    for invented in ("Week 1", "Sprint", "$", "man-day", "Milestone", "on track", "successfully"):
        assert invented not in plan


def test_risks_with_a_clean_qa_report_have_no_defect_rows():
    risks = documents()[0][RISKS_FILE]

    assert risks.startswith("# Risks — Task Manager\n")
    assert "No open defects: QA reported 8 of 8 checks passed and none failed." in risks
    assert "Open defect:" not in risks and "not repaired" not in risks
    assert "Data is stored only in the browser (localStorage)" in risks
    assert "Storage key `bunyan_task`" in risks
    assert "QA covers 8 fixed checks, not every acceptance criterion" in risks
    numbers = [int(re.match(r"\| R-(\d+)", row).group(1)) for row in table_rows(risks)]
    assert numbers == list(range(1, len(numbers) + 1))


def test_qa_warnings_are_carried_over_word_for_word():
    warning = "Required enum fields with a default cannot be left empty, so empty-input checks skip them: priority, status"
    risks = documents(report=qa_report(warnings=[warning]))[0][RISKS_FILE]
    assert f"| QA warning | QA report | {warning} |" in risks


# ---------- Arabic ----------


def test_arabic_requirements_give_arabic_documents():
    docs, req = documents("scenario_b_inventory_ar")
    plan, risks = docs[PLAN_FILE], docs[RISKS_FILE]

    assert plan.startswith(f"# خطة المشروع — {req['app']['name']}\n")
    assert risks.startswith(f"# المخاطر — {req['app']['name']}\n")
    assert "## ملخص الحالة" in plan and "## المراحل" in plan and "## غير متوفر" in plan
    assert "- نتيجة الاختبار: ناجح: 8 من 8 فحوص ناجحة" in plan
    assert f"- الكيان: {req['entities'][0]['label']} (`Product`)" in plan
    assert "البيانات محفوظة في المتصفح فقط (localStorage)" in risks
    assert "مفتاح التخزين `bunyan_product`" in risks
    assert "لا توجد عيوب مفتوحة" in risks
    for english in ("Project plan", "Summary", "Not available", "Open defects", "Passed:"):
        assert english not in plan and english not in risks


def test_arabic_out_of_scope_items_become_risks():
    docs, req = documents("appointment_booking_en")
    item = req["out_of_scope"][0]

    assert f"Requested feature left out: {item['feature']}" in docs[RISKS_FILE]
    assert item["feature"] in docs[PLAN_FILE]
    assert "Replaced with an alternative" in docs[PLAN_FILE]


# ---------- QA found defects ----------


def test_failed_checks_are_open_defects_with_their_real_message():
    report = qa_report({"persist_after_refresh": "failed", "edit_item": "failed"})
    run = run_state("failed", metrics={"pass_rate": 0.75, "checks_passed": 6, "checks_total": 8, "run_time_seconds": 9.1})
    docs, _ = documents(report=report, run=run)
    plan, risks = docs[PLAN_FILE], docs[RISKS_FILE]

    assert "- Test result: Defects found: 6 of 8 checks passed, 2 failed" in plan
    assert "| Testing | test_report.json | Defects found: 6 of 8 checks passed, 2 failed |" in plan
    assert "No open defects" not in risks
    assert "- `edit_item`\n- `persist_after_refresh`" in risks
    assert "| Open defect: check `persist_after_refresh` failed | QA report | Expected 1 row, received 0 (persist_after_refresh) (Evidence: `qa_evidence/persist_after_refresh-screenshot.png`) |" in risks
    assert "Call log" not in risks  # only the first line of the error
    assert "| Defects were not repaired | Run status | 2 failed check(s) remain. No repair was attempted: repair attempts 0 of 2. |" in risks
    rows = table_rows(risks)
    assert "Open defect:" in rows[0] and "Open defect:" in rows[1]  # defects come first


def test_skipped_checks_are_reported_as_unverified_not_as_defects():
    report = qa_report({"reject_incomplete_input": "skipped", "error_message_visible": "skipped"})
    docs, _ = documents(report=report)

    assert "- Test result: Passed: 6 of 8 checks passed, 2 skipped (not applicable)" in docs[PLAN_FILE]
    assert "Check `reject_incomplete_input` was skipped, so that behaviour is not verified" in docs[RISKS_FILE]
    assert "No required field can be left empty" in docs[RISKS_FILE]
    assert "Open defect:" not in docs[RISKS_FILE]
    assert "No open defects: QA reported 6 of 8 checks passed and none failed." in docs[RISKS_FILE]


# ---------- QA missing or blocked, optional data missing ----------


def test_without_a_qa_report_nothing_is_claimed_about_quality():
    docs, _ = documents(report=None, run=run_state("not_run", metrics=None))
    plan, risks = docs[PLAN_FILE], docs[RISKS_FILE]

    assert "- Test result: Not run: QA was switched off for this run" in plan
    assert "- Run time: Not available" in plan
    assert "| Testing started | Not available |" in plan
    assert "Unknown: the application was not tested." in risks
    assert "| The application was not tested | Run status |" in risks
    assert "checks passed" not in plan and "No open defects" not in risks
    assert "QA covers 8 fixed checks" not in risks


def test_blocked_qa_is_not_a_pass():
    statuses = {check_id: "not_run" for check_id in CHECK_IDS}
    report = qa_report(statuses, blocked_reason="Cannot test requirements.json:\n- display_field must be a text field")
    docs, _ = documents(report=report, run=run_state("blocked", metrics=None))

    assert "Not verified: QA could not test the application" in docs[PLAN_FILE]
    assert "| The application could not be tested | QA report | Cannot test requirements.json: |" in docs[RISKS_FILE]
    assert "Unknown: the application was not tested." in docs[RISKS_FILE]
    assert "No open defects" not in docs[RISKS_FILE]


def test_missing_optional_information_is_marked_not_available():
    req = requirements("task_manager_en")
    for key in ("assumptions", "out_of_scope", "clarification_questions", "user_stories", "acceptance_criteria"):
        req.pop(key)
    req["app"].pop("description")
    docs = build_documents(req, build_architecture(requirements("task_manager_en")), None, None, None, NOW)
    plan = docs[PLAN_FILE]

    assert "- Description: Not available" in plan
    assert "- User stories: 0" in plan
    assert "## Deliverables\n\nNot available" in plan
    assert "| Project created | Not available |" in plan
    assert "### Left out of this version\n\nNone." in plan
    assert "### Assumptions made by the Business Analyst\n\nNone." in plan
    assert "None" != plan and "null" not in plan and "{" not in plan


def test_text_with_pipes_and_newlines_cannot_break_the_tables():
    req = requirements("task_manager_en")
    req["assumptions"] = ["first | second\nthird"]
    docs = build_documents(req, build_architecture(requirements("task_manager_en")), qa_report(), run_state(), FILES, NOW)

    row = next(line for line in docs[RISKS_FILE].splitlines() if "second" in line)
    assert row.endswith("| first \\| second third |")


@pytest.mark.parametrize("bad_requirements", [None, {}, {"app": {}}, {"app": {"name": ""}}, "text"])
def test_unusable_requirements_are_refused(bad_requirements):
    with pytest.raises(ProjectManagerError):
        build_documents(bad_requirements, build_architecture(requirements("task_manager_en")))


@pytest.mark.parametrize("bad_architecture", [None, {}, {"entity": []}])
def test_unusable_architecture_is_refused(bad_architecture):
    with pytest.raises(ProjectManagerError):
        build_documents(requirements("task_manager_en"), bad_architecture)


# ---------- writing ----------


def test_write_documents_creates_both_files(tmp_path):
    req = requirements("scenario_b_inventory_ar")
    written = write_documents(req, build_architecture(req), tmp_path / "project", qa_report(), run_state(), FILES, NOW)

    assert set(written) == {PLAN_FILE, RISKS_FILE}
    assert sorted(p.name for p in (tmp_path / "project").iterdir()) == ["project_plan.md", "risks.md"]
    assert (tmp_path / "project" / PLAN_FILE).read_text(encoding="utf-8").startswith("# خطة المشروع")


def test_same_inputs_give_the_same_documents():
    first, _ = documents()
    second, _ = documents()
    assert first == second


def test_documents_contain_no_server_paths_or_secrets():
    docs, _ = documents()
    for text in docs.values():
        assert "/Users/" not in text and "backend/data" not in text and "API_KEY" not in text
