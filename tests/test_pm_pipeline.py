"""Project Manager stage of the pipeline: Architect -> Developer -> QA -> PM -> completed.

Offline. QA results come from the stand-in runner of tests/test_qa_pipeline.py
(reports in Sara's format); the Project Manager itself is the real one. The run
with real Playwright and all eight files is in tests/test_qa_pipeline.py.
"""

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import main, storage
from backend.orchestrator import pipeline, run_pipeline
from test_qa_pipeline import (
    ALL_FILES,
    CHECK_IDS,
    Recorder,
    StandInRunner,
    files_in,
    load_requirements,
    make_project,
    report_in_saras_format,
)

APP_AND_REPORT = ["app/app.js", "app/index.html", "app/style.css", "architecture.json", "requirements.json", "test_report.json"]


def run(tmp_path, runner=None, requirements="task_manager_en"):
    recorder = Recorder()
    project = run_pipeline(make_project(load_requirements(requirements)), tmp_path, recorder, qa_runner=runner)
    return project, recorder


def plan(folder):
    return (Path(folder) / "project_plan.md").read_text(encoding="utf-8")


def risks(folder):
    return (Path(folder) / "risks.md").read_text(encoding="utf-8")


# ---------- the stage ----------


def test_pm_runs_after_qa_and_before_completed(tmp_path):
    project, recorder = run(tmp_path, StandInRunner())

    assert recorder.steps == [
        ("designing", "software_architect"),
        ("developing", "developer"),
        ("testing", "qa_tester"),
        ("documenting", "project_manager"),
        ("completed", None),
    ]
    assert project["status"] == "completed" and project["error"] is None
    assert files_in(tmp_path) == ALL_FILES


def test_both_documents_are_listed_only_once_they_exist(tmp_path):
    project, recorder = run(tmp_path, StandInRunner())

    names = lambda state: [a["name"] for a in state["artifacts"]]
    documenting = next(p for p in recorder.saved if p["status"] == "documenting")
    assert "project_plan.md" not in names(documenting) and "risks.md" not in names(documenting)
    assert names(project) == [
        "requirements.json", "architecture.json", "index.html", "style.css", "app.js",
        "test_report.json", "project_plan.md", "risks.md",
    ]
    for artifact in project["artifacts"]:
        assert (tmp_path / artifact["path"]).stat().st_size > 0


def test_qa_metrics_and_summary_are_unchanged_by_the_pm(tmp_path):
    project, recorder = run(tmp_path, StandInRunner(report_in_saras_format({"edit_item": "failed"})))

    after_qa = next(p for p in recorder.saved if p["status"] == "documenting")
    assert project["metrics"] == after_qa["metrics"]
    assert project["qa"] == after_qa["qa"]
    assert project["metrics"]["checks_passed"] == 7 and project["qa"]["status"] == "failed"
    assert project["repair_attempt"] == 0


# ---------- documents reflect the real run ----------


def test_documents_for_a_passed_run(tmp_path):
    project, _ = run(tmp_path, StandInRunner())
    requirements = load_requirements("task_manager_en")

    text = plan(tmp_path)
    assert text.startswith("# Project plan — Task Manager\n")
    assert "- Test result: Passed: 8 of 8 checks passed" in text
    assert f"- Run time: {project['metrics']['run_time_seconds']} seconds" in text
    assert f"- Acceptance criteria: {len(requirements['acceptance_criteria'])}" in text
    for name in ("requirements.json", "architecture.json", "index.html", "style.css", "app.js", "test_report.json"):
        relative = f"app/{name}" if name in ("index.html", "style.css", "app.js") else name
        assert f"| `{name}` | {(tmp_path / relative).stat().st_size} bytes |" in text  # real sizes on disk
    assert "No open defects: QA reported 8 of 8 checks passed and none failed." in risks(tmp_path)
    assert "Storage key `bunyan_task`" in risks(tmp_path)


def test_documents_for_a_run_with_defects(tmp_path):
    report = report_in_saras_format({"persist_after_refresh": "failed"})
    project, _ = run(tmp_path, StandInRunner(report))

    assert project["status"] == "completed" and project["qa"]["status"] == "failed"
    assert "- Test result: Defects found: 7 of 8 checks passed, 1 failed" in plan(tmp_path)
    text = risks(tmp_path)
    assert "- `persist_after_refresh`" in text
    assert "Open defect: check `persist_after_refresh` failed" in text
    assert "persist_after_refresh went wrong" in text  # the message from the QA report
    assert "No repair was attempted: repair attempts 0 of 2." in text
    assert "No open defects" not in text


def test_documents_when_qa_is_switched_off(tmp_path):
    project, recorder = run(tmp_path)  # BUNYAN_QA=off in tests

    assert project["status"] == "completed" and project["qa"]["status"] == "not_run"
    assert recorder.steps[-2:] == [("documenting", "project_manager"), ("completed", None)]
    assert "- Test result: Not run: QA was switched off for this run" in plan(tmp_path)
    assert "- Run time: Not available" in plan(tmp_path)
    assert "The application was not tested" in risks(tmp_path)
    assert "checks passed" not in plan(tmp_path) and "No open defects" not in risks(tmp_path)


def test_arabic_project_gets_arabic_documents(tmp_path):
    run(tmp_path, StandInRunner(report_in_saras_format(entity="Product")), requirements="scenario_b_inventory_ar")

    assert plan(tmp_path).startswith("# خطة المشروع — ")
    assert "- نتيجة الاختبار: ناجح: 8 من 8 فحوص ناجحة" in plan(tmp_path)
    assert risks(tmp_path).startswith("# المخاطر — ")
    assert "مفتاح التخزين `bunyan_product`" in risks(tmp_path)


def test_documents_have_no_server_paths(tmp_path):
    run(tmp_path, StandInRunner(report_in_saras_format({"edit_item": "failed"})))
    for text in (plan(tmp_path), risks(tmp_path)):
        assert str(tmp_path) not in text and "/Users/" not in text


# ---------- when QA is blocked the run has already failed: no PM ----------


def test_blocked_qa_still_fails_the_run_without_pm_documents(tmp_path):
    statuses = {check_id: "not_run" for check_id in CHECK_IDS}
    report = report_in_saras_format(statuses, blocked_reason="Cannot test this app")
    project, recorder = run(tmp_path, StandInRunner(report))

    assert project["status"] == "failed" and project["error"]["code"] == "qa_blocked"
    assert "documenting" not in [status for status, _ in recorder.steps]
    assert files_in(tmp_path) == APP_AND_REPORT


def test_crashed_qa_still_fails_the_run_without_pm_documents(tmp_path):
    project, recorder = run(tmp_path, StandInRunner(error=RuntimeError("npx not found. Install Node.js first.")))

    assert project["error"]["code"] == "qa_failed"
    assert "documenting" not in [status for status, _ in recorder.steps]
    assert not (tmp_path / "project_plan.md").exists() and not (tmp_path / "risks.md").exists()


# ---------- PM failures ----------


def assert_pm_failed_but_app_kept(project, recorder, tmp_path):
    assert project["status"] == "failed"
    assert project["current_agent"] == "project_manager"
    assert project["error"]["code"] == "documentation_failed"
    assert recorder.steps[-2:] == [("documenting", "project_manager"), ("failed", "project_manager")]
    assert recorder.saved[-1]["error"] == project["error"]
    assert "completed" not in [status for status, _ in recorder.steps]
    assert set(APP_AND_REPORT) <= set(files_in(tmp_path))  # nothing generated earlier was lost
    assert project["metrics"]["checks_passed"] == 8 and project["qa"]["status"] == "passed"


def test_pm_crash_fails_the_run_and_keeps_the_app(tmp_path, monkeypatch):
    def crash(*args, **kwargs):
        raise RuntimeError("template exploded")

    monkeypatch.setattr(pipeline, "write_documents", crash)
    project, recorder = run(tmp_path, StandInRunner())

    assert_pm_failed_but_app_kept(project, recorder, tmp_path)
    assert "template exploded" in project["error"]["message"]
    assert [a["name"] for a in project["artifacts"]][-1] == "test_report.json"  # PM files are not advertised


def test_pm_that_writes_only_one_document_is_not_completed(tmp_path, monkeypatch):
    def only_the_plan(requirements, architecture, output_dir, **kwargs):
        (Path(output_dir) / "project_plan.md").write_text("# plan", encoding="utf-8")

    monkeypatch.setattr(pipeline, "write_documents", only_the_plan)
    project, recorder = run(tmp_path, StandInRunner())

    assert_pm_failed_but_app_kept(project, recorder, tmp_path)
    assert project["error"]["message"] == "Project documents are missing or empty: risks.md"


def test_pm_file_error_fails_the_run_without_a_server_path(tmp_path):
    (tmp_path / "risks.md").mkdir(parents=True)  # a folder sits where the document should go
    project, recorder = run(tmp_path, StandInRunner())

    assert project["status"] == "failed" and project["error"]["code"] == "documentation_failed"
    assert project["current_agent"] == "project_manager"
    assert str(tmp_path) not in project["error"]["message"]
    assert (tmp_path / "app" / "app.js").is_file()


def test_pm_refusing_its_inputs_fails_the_run(tmp_path, monkeypatch):
    real_build = pipeline.build_architecture

    def architecture_without_entity(requirements):
        architecture = real_build(requirements)
        monkeypatch.setattr(pipeline, "generate", lambda r, a, out: _write_app(out))
        architecture.pop("entity")
        return architecture

    def _write_app(out):
        out.mkdir(parents=True, exist_ok=True)
        for name in ("index.html", "style.css", "app.js"):
            (out / name).write_text("x", encoding="utf-8")

    monkeypatch.setattr(pipeline, "build_architecture", architecture_without_entity)
    project, _ = run(tmp_path, StandInRunner())

    assert project["error"]["code"] == "documentation_failed"
    assert "entity" in project["error"]["message"]


# ---------- API: artifacts, ZIP, restart ----------


@pytest.fixture
def client():
    return TestClient(main.app)


def approve(client, idea="A simple task manager with a title, due date and status"):
    pid = client.post("/projects", json={"prompt": idea}).json()["project_id"]
    assert client.post(f"/projects/{pid}/approve", json={"approved": True}).json()["status"] == "designing"
    return pid


def test_api_serves_both_documents_and_zip_has_eight_files(client, monkeypatch, qa_on):
    monkeypatch.setattr(pipeline, "run_qa", StandInRunner())
    pid = approve(client)

    project = client.get(f"/projects/{pid}").json()
    assert project["status"] == "completed" and project["current_agent"] is None
    assert len(project["artifacts"]) == 8 and all(a["available"] for a in project["artifacts"])

    for name in ("project_plan.md", "risks.md"):
        response = client.get(f"/projects/{pid}/artifacts/{name}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
        assert response.content == (storage.project_dir(pid) / name).read_bytes()
    assert "Passed: 8 of 8 checks passed" in client.get(f"/projects/{pid}/artifacts/project_plan.md").text

    archive = zipfile.ZipFile(io.BytesIO(client.get(f"/projects/{pid}/download").content))
    assert archive.testzip() is None
    assert sorted(archive.namelist()) == ALL_FILES and len(ALL_FILES) == 8
    assert archive.read("risks.md") == (storage.project_dir(pid) / "risks.md").read_bytes()
    assert client.get(f"/projects/{pid}/preview/project_plan.md").status_code == 404  # preview stays app-only


def test_api_pm_failure_keeps_app_previewable_and_downloadable(client, monkeypatch, qa_on):
    monkeypatch.setattr(pipeline, "run_qa", StandInRunner())
    monkeypatch.setattr(pipeline, "write_documents", lambda *a, **k: (_ for _ in ()).throw(OSError(28, "No space left on device")))
    pid = approve(client)

    project = client.get(f"/projects/{pid}").json()
    assert project["status"] == "failed"
    assert project["error"] == {
        "code": "documentation_failed",
        "message": "Could not write the project documents: OSError: No space left on device",
    }
    assert project["metrics"]["checks_passed"] == 8
    assert client.get(f"/projects/{pid}/preview/").status_code == 200
    assert client.get(f"/projects/{pid}/artifacts/project_plan.md").status_code == 404
    archive = zipfile.ZipFile(io.BytesIO(client.get(f"/projects/{pid}/download").content))
    assert sorted(archive.namelist()) == APP_AND_REPORT
    assert client.post(f"/projects/{pid}/approve", json={"approved": True}).status_code == 409


def test_run_interrupted_while_documenting_is_recovered_on_startup(client):
    pid = client.post("/projects", json={"prompt": "A simple task manager"}).json()["project_id"]
    project = storage.load_project(pid)
    project.update(status="documenting", current_agent="project_manager", requirements_approved=True)
    storage.save_project(project)

    assert main.recover_interrupted_projects() == [pid]
    assert client.get(f"/projects/{pid}").json()["error"]["code"] == "pipeline_interrupted"
