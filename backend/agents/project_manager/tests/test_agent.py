"""Offline tests: facts, stages, risk rules, documents, CLI and the LLM step with a fake client."""

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.agents.project_manager import PMInput, run_project_manager, write_outputs
from backend.agents.project_manager.__main__ import main
from backend.agents.project_manager.arabic import count
from backend.agents.project_manager.config import ConfigError, Settings, get_settings
from backend.agents.project_manager.llm import parse_answer, LLMStepError

from .conftest import SAMPLE_NAMES, SAMPLES, load_input


def stage(result, key):
    return next(s for s in result.stages if s.key == key)


def risk_sources(result):
    return [r.source for r in result.risks]


# ---------- every sample ----------
@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_samples_produce_both_documents(name):
    result = run_project_manager(load_input(name))
    assert result.mode == "rules"
    assert result.project_plan_md.startswith("# ")
    assert result.risks_md.startswith("# ")
    assert len(result.stages) == 5
    assert all(r.id.startswith("R-") for r in result.risks)
    assert [r.id for r in result.risks] == [f"R-{i}" for i in range(1, len(result.risks) + 1)]


@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_outputs_are_deterministic(name):
    assert run_project_manager(load_input(name)) == run_project_manager(load_input(name))


@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_committed_outputs_are_up_to_date(name):
    """samples/outputs must match what the agent writes today (run regenerate_samples.py)."""
    result = run_project_manager(load_input(name))
    out = SAMPLES / "outputs" / name
    assert (out / "project_plan.md").read_text(encoding="utf-8") == result.project_plan_md
    assert (out / "risks.md").read_text(encoding="utf-8") == result.risks_md


# ---------- scenarios ----------
def test_completed_run_with_one_repair():
    result = run_project_manager(load_input("inventory_dialect_ar"))
    assert result.status == "complete"
    assert all(s.status == "done" for s in result.stages)
    closed = [r for r in result.risks if r.status == "closed"]
    assert len(closed) == 1 and closed[0].source == "test_report.run.attempt"
    assert result.risks[-1].status == "closed", "closed risks come last"
    assert "إصلاح واحد" in result.summary
    assert "ضمن الهدف" in result.project_plan_md


def test_english_documents_for_english_app():
    result = run_project_manager(load_input("task_manager_en"))
    assert result.language == "en"
    assert "# Project plan: Task Manager" in result.project_plan_md
    assert "| Stage | Owner | Output | Status |" in result.project_plan_md
    assert not any(r.status == "closed" for r in result.risks)


def test_failing_check_after_two_repairs_is_the_top_risk():
    result = run_project_manager(load_input("appointment_tests_failing_en"))
    assert result.status == "partial"
    assert stage(result, "tests").status == "failed"
    top = result.risks[0]
    assert top.source == "test_report.checks.persist_after_refresh"
    assert (top.likelihood, top.impact) == ("high", "high")
    assert "Both repair attempts are used" in top.mitigation
    assert "run_time_seconds" in risk_sources(result)  # 141 s > 90 s target
    assert any(s.startswith("architecture.warnings[") for s in risk_sources(result))
    assert "above the 90 s target" in result.project_plan_md


def test_failing_check_with_a_repair_left():
    data = load_input("appointment_tests_failing_en")
    data["repair_attempt"] = 0
    data["test_report"]["run"]["attempt"] = 0
    result = run_project_manager(data)
    assert stage(result, "tests").status == "in_progress"
    assert "went back to the Developer" in result.risks[0].mitigation


def test_stopped_run_is_partial_and_marks_where_it_stopped():
    result = run_project_manager(load_input("stopped_at_structure_ar"))
    assert result.status == "partial"
    statuses = [s.status for s in result.stages]
    assert statuses == ["done", "failed", "not_started", "not_started", "done"]
    assert result.risks[0].source == "workflow.status=failed"
    assert "توقف عند: تصميم الهيكل" in result.summary
    assert "لم تُسجَّل مدد المراحل" in result.project_plan_md


def test_running_build_marks_the_current_stage_in_progress():
    data = load_input("inventory_dialect_ar")
    data.update(status="developing", test_report=None, generated_files=["index.html"])
    result = run_project_manager(data)
    assert [s.status for s in result.stages][:4] == ["done", "done", "in_progress", "not_started"]


def test_completed_without_test_report_is_flagged():
    data = load_input("inventory_dialect_ar")
    data["test_report"] = None
    result = run_project_manager(data)
    assert "test_report.json missing" in risk_sources(result)


def test_blocked_and_skipped_checks_are_risks():
    data = load_input("task_manager_en")
    rep = data["test_report"]
    rep["run"]["blocked_reason"] = "browser did not start"
    rep["summary"].update(passed=6, skipped=2, all_passed=False)
    for c in rep["checks"][-2:]:
        c["status"] = "skipped"
    result = run_project_manager(data)
    sources = risk_sources(result)
    assert "test_report.run.blocked_reason" in sources
    assert "test_report.summary.skipped" in sources


# ---------- input contract ----------
def test_only_requirements_is_required():
    data = load_input("task_manager_en")
    result = run_project_manager({"requirements": data["requirements"]})
    assert result.status == "partial"
    assert stage(result, "structure").status == "in_progress"


def test_unknown_fields_are_ignored():
    data = load_input("task_manager_en")
    data["something_new"] = {"from": "another agent"}
    data["architecture"]["future_key"] = [1, 2, 3]
    run_project_manager(data)


def test_requirements_without_app_or_entities_are_rejected():
    with pytest.raises(ValidationError):
        PMInput.model_validate({"requirements": {"status": "ready_for_review"}})


def test_language_override():
    data = load_input("task_manager_en")
    data["language"] = "ar"
    assert run_project_manager(data).project_plan_md.startswith("# خطة المشروع")


def test_table_cells_escape_pipes():
    data = load_input("task_manager_en")
    data["requirements"]["out_of_scope"] = [{"feature": "Import | export", "reason": "r", "alternative": "a | b"}]
    risks_md = run_project_manager(data).risks_md
    assert "Import \\| export" in risks_md and "a \\| b" in risks_md


# ---------- files ----------
def test_write_outputs_writes_exactly_two_files(tmp_path):
    result = run_project_manager(load_input("inventory_dialect_ar"))
    paths = write_outputs(result, tmp_path / "run")
    assert sorted(p.name for p in (tmp_path / "run").iterdir()) == ["project_plan.md", "risks.md"]
    assert paths["risks.md"].read_text(encoding="utf-8") == result.risks_md


# ---------- Arabic numbers ----------
@pytest.mark.parametrize("n,word,expected", [
    (1, "field", "حقل واحد"), (2, "field", "حقلان"), (3, "field", "3 حقول"), (10, "field", "10 حقول"),
    (11, "field", "11 حقلاً"), (8, "check", "8 فحوصات"), (2, "screen", "شاشتان"), (9, "second", "9 ثوانٍ"),
    (90, "second", "90 ثانية"), (1, "repair", "إصلاح واحد"), (103, "check", "103 فحوصات"),
])
def test_arabic_count(n, word, expected):
    assert count(n, word) == expected


# ---------- LLM step (fake client, no network) ----------
class FakeClient:
    def __init__(self, text, stop_reason="end_turn"):
        self.text, self.stop_reason, self.calls = text, stop_reason, []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=self.text)])


LLM_SETTINGS = Settings(mode="llm", provider="anthropic", model="claude-opus-5-5")
GOOD = json.dumps({
    "summary": "Task Manager is complete and passed all 8 checks on the first run. The main open risk is data loss.",
    "additional_risks": [{"title": "Users may expect reminders", "likelihood": "low", "impact": "low",
                          "mitigation": "Mention due dates on the list screen.", "source": "requirements.out_of_scope"}],
})


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


def test_llm_summary_and_extra_risk_are_merged(api_key):
    client = FakeClient(f"```json\n{GOOD}\n```")
    result = run_project_manager(load_input("task_manager_en"), settings=LLM_SETTINGS, client=client)
    assert result.mode == "llm" and not result.warnings
    assert result.summary.startswith("Task Manager is complete")
    assert result.risks[-1].id == "R-L1" and result.risks[-1].source == "llm: requirements.out_of_scope"
    assert "R-L1" in result.risks_md
    sent = client.calls[0]
    assert sent["model"] == "claude-opus-5-5"
    assert "test-key-not-real" not in json.dumps(sent, ensure_ascii=False)


def test_llm_cannot_change_rule_risks_or_stages(api_key):
    rules = run_project_manager(load_input("task_manager_en"))
    llm = run_project_manager(load_input("task_manager_en"), settings=LLM_SETTINGS, client=FakeClient(GOOD))
    assert llm.risks[: len(rules.risks)] == rules.risks
    assert llm.stages == rules.stages


@pytest.mark.parametrize("text,stop", [("not json at all", "end_turn"), ('{"summary": "short"}', "end_turn"),
                                       (GOOD, "refusal"), (GOOD, "max_tokens")])
def test_llm_failure_falls_back_to_rules(api_key, text, stop):
    result = run_project_manager(load_input("task_manager_en"), settings=LLM_SETTINGS, client=FakeClient(text, stop))
    assert result.mode == "rules"
    assert result.warnings and result.warnings[0].startswith("LLM step skipped")
    assert result == run_project_manager(load_input("task_manager_en")).model_copy(update={"warnings": result.warnings})


def test_llm_more_than_three_extra_risks_is_rejected():
    many = json.loads(GOOD)
    many["additional_risks"] *= 4
    with pytest.raises(LLMStepError):
        parse_answer(json.dumps(many))


def test_llm_mode_without_key_is_a_config_error():
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        run_project_manager(load_input("task_manager_en"), settings=LLM_SETTINGS, client=FakeClient(GOOD))


def test_settings_accept_mock_as_rules(monkeypatch):
    monkeypatch.setenv("PM_MODE", "mock")
    assert get_settings().mode == "rules"
    with pytest.raises(ConfigError):
        get_settings("fast")


# ---------- CLI ----------
def test_cli_writes_files(tmp_path, capsys):
    code = main(["--input", str(SAMPLES / "inputs" / "inventory_dialect_ar.json"), "--out-dir", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "project_plan.md").exists() and (tmp_path / "risks.md").exists()
    assert "status: complete" in capsys.readouterr().err


def test_cli_separate_files(tmp_path, capsys):
    data = load_input("task_manager_en")
    for key in ("requirements", "architecture", "test_report"):
        (tmp_path / f"{key}.json").write_text(json.dumps(data[key]), encoding="utf-8")
    code = main(["--requirements", str(tmp_path / "requirements.json"), "--architecture", str(tmp_path / "architecture.json"),
                 "--test-report", str(tmp_path / "test_report.json"), "--files", "index.html", "style.css", "app.js", "--json"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "complete"


def test_cli_exit_codes(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"requirements": {}}), encoding="utf-8")
    assert main(["--input", str(bad)]) == 1
    assert main(["--input", str(tmp_path / "missing.json")]) == 2
    assert main(["--schema"]) == 0
