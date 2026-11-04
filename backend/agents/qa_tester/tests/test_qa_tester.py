"""Tests for the QA Tester Agent.

Run from the repository root:

    python -m pytest backend/agents/qa_tester/tests -v
"""

import csv
import shutil

import pytest
from pydantic import ValidationError

from backend.agents.qa_tester import run_qa
from backend.agents.qa_tester import runner
from backend.agents.qa_tester.quality_log import append_run
from backend.agents.qa_tester.schema import QAReport

FIXTURE_APP = "tests/e2e/fixtures/task-manager"
REQUIREMENTS = "backend/agents/business_analyst/samples/outputs/task_manager_en.requirements.json"
CHECK_IDS = [
    "create_item", "list_items", "edit_item", "delete_item",
    "persist_after_refresh", "reject_incomplete_input", "empty_state", "error_message_visible",
]
needs_node = pytest.mark.skipif(shutil.which("npx") is None, reason="Node.js (npx) is not installed")


def make_report(statuses):
    """A small valid report where check i has statuses[i]."""
    checks = [
        {
            "id": check_id,
            "description": "test",
            "status": status,
            "duration_ms": 10,
            "related_criteria": [],
            "error": {"message": "boom"} if status == "failed" else None,
            "skip_reason": None,
            "evidence": {"screenshot": None, "trace": None},
        }
        for check_id, status in zip(CHECK_IDS, statuses)
    ]
    passed = statuses.count("passed")
    return {
        "schema_version": "0.1.0-proposal",
        "app": {"name": "Task Manager", "language": "en"},
        "entity": "Task",
        "inputs": {"is_harness_fixture": True},
        "run": {
            "attempt": 0, "max_repair_attempts": 2,
            "started_at": "2026-11-04T10:00:00Z", "finished_at": "2026-11-04T10:00:07Z",
            "duration_ms": 7000, "browser": "chromium", "blocked_reason": None,
        },
        "summary": {
            "total": 8, "passed": passed, "failed": statuses.count("failed"),
            "skipped": statuses.count("skipped"), "not_run": statuses.count("not_run"),
            "pass_rate": passed / 8, "all_passed": passed == 8,
        },
        "checks": checks,
        "defects": [
            {"check_id": c["id"], "message": "boom", "evidence": c["evidence"]}
            for c in checks if c["status"] == "failed"
        ],
        "warnings": [],
    }


# ---------- input checks (fast, no browser) ----------

def test_rejects_folder_without_index_html():
    with pytest.raises(FileNotFoundError):
        run_qa("tests/e2e", REQUIREMENTS)


def test_rejects_missing_requirements():
    with pytest.raises(FileNotFoundError):
        run_qa(FIXTURE_APP, "does/not/exist.json")


def test_rejects_third_repair_attempt():
    with pytest.raises(ValueError):
        run_qa(FIXTURE_APP, REQUIREMENTS, attempt=3)


# ---------- report shape ----------

def test_schema_accepts_valid_report():
    QAReport.model_validate(make_report(["passed"] * 7 + ["failed"]))


def test_schema_rejects_fake_pass():
    report = make_report(["passed"] * 7 + ["failed"])
    report["summary"]["passed"] = 8  # claims 8 passed, but only 7 really did
    with pytest.raises(ValidationError):
        QAReport.model_validate(report)


def test_schema_requires_exactly_8_checks():
    report = make_report(["passed"] * 8)
    report["checks"] = report["checks"][:7]
    with pytest.raises(ValidationError):
        QAReport.model_validate(report)


# ---------- quality log ----------

def test_quality_log_adds_one_line_per_run(tmp_path):
    log = tmp_path / "quality_log.csv"
    append_run(make_report(["passed"] * 8), log_path=log)
    append_run(make_report(["passed"] * 7 + ["failed"]), log_path=log)

    with open(log, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]["passed"] == "8"
    assert rows[1]["failed_checks"] == "error_message_visible"


# ---------- real runs on the harness fixture (slow, needs Node.js) ----------

@needs_node
def test_real_run_on_fixture_passes_all_8(monkeypatch):
    monkeypatch.setattr(runner, "append_run", lambda report: None)  # keep the real log clean
    report = run_qa(FIXTURE_APP, REQUIREMENTS)
    assert report["summary"]["passed"] == 8
    assert report["inputs"]["is_harness_fixture"] is True


@needs_node
def test_real_run_finds_storage_defect(monkeypatch):
    monkeypatch.setattr(runner, "append_run", lambda report: None)
    report = run_qa(FIXTURE_APP, REQUIREMENTS, attempt=1, app_path="/?bug=no-persist")
    assert report["run"]["attempt"] == 1
    assert [d["check_id"] for d in report["defects"]] == ["persist_after_refresh"]