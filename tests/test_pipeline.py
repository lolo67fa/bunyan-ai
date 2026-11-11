"""Tests for the MVP pipeline: approved requirements -> Architect -> Developer -> files.

Offline: no LLM, no network, no Node.js. Requirements come from the Business
Analyst's own sample outputs.
"""

import copy
import json
from pathlib import Path

import pytest

from backend.agents.architect import ArchitectureDocument
from backend.agents.developer import DeveloperError
from backend.orchestrator import PipelineNotApproved, pipeline, run_pipeline

SAMPLES = Path(__file__).resolve().parents[1] / "backend" / "agents" / "business_analyst" / "samples" / "outputs"
EXPECTED_FILES = [
    "app/app.js",
    "app/index.html",
    "app/style.css",
    "architecture.json",
    "requirements.json",
]


def load_requirements(name):
    return json.loads((SAMPLES / f"{name}.requirements.json").read_text(encoding="utf-8"))


def make_project(requirements, approved=True):
    """A project in the shape backend/main.py stores after the user approves."""
    return {
        "project_id": "11111111-2222-3333-4444-555555555555",
        "idea": "test idea",
        "status": "approved",
        "current_agent": "business_analyst",
        "requirements": requirements,
        "requirements_approved": approved,
        "artifacts": [],
        "repair_attempt": 0,
        "metrics": None,
        "error": None,
        "created_at": "2026-11-11T00:00:00+00:00",
        "updated_at": "2026-11-11T00:00:00+00:00",
    }


class Recorder:
    """Stands in for the storage callback and keeps a copy of every saved state."""

    def __init__(self):
        self.saved = []

    def __call__(self, project):
        self.saved.append(copy.deepcopy(project))

    @property
    def steps(self):
        return [(p["status"], p["current_agent"]) for p in self.saved]


def files_in(workdir):
    return sorted(p.relative_to(workdir).as_posix() for p in Path(workdir).rglob("*") if p.is_file())


@pytest.fixture
def recorder():
    return Recorder()


# ---------- success ----------


def test_english_task_manager_is_generated(tmp_path, recorder):
    requirements = load_requirements("task_manager_en")
    project = run_pipeline(make_project(requirements), tmp_path, recorder)

    assert project["status"] == "completed"
    assert project["current_agent"] is None
    assert project["error"] is None
    assert files_in(tmp_path) == EXPECTED_FILES

    architecture = json.loads((tmp_path / "architecture.json").read_text(encoding="utf-8"))
    ArchitectureDocument.model_validate(architecture)
    assert architecture["entity"]["name"] == "Task"
    assert json.loads((tmp_path / "requirements.json").read_text(encoding="utf-8")) == requirements

    script = (tmp_path / "app" / "app.js").read_text(encoding="utf-8")
    assert "__BUNYAN_CONFIG__" not in script
    assert '"key":"bunyan_task"' in script  # the real architecture was injected
    assert "localStorage" in script
    html = (tmp_path / "app" / "index.html").read_text(encoding="utf-8")
    assert 'data-testid="btn-add"' in html and 'src="app.js"' in html


def test_arabic_single_entity_app_is_generated(tmp_path, recorder):
    requirements = load_requirements("scenario_b_inventory_ar")
    project = run_pipeline(make_project(requirements), tmp_path, recorder)

    assert project["status"] == "completed"
    assert files_in(tmp_path) == EXPECTED_FILES

    architecture = json.loads((tmp_path / "architecture.json").read_text(encoding="utf-8"))
    assert architecture["app"]["language"] == "ar"
    assert architecture["app"]["direction"] == "rtl"
    script = (tmp_path / "app" / "app.js").read_text(encoding="utf-8")
    assert "__BUNYAN_CONFIG__" not in script
    assert requirements["app"]["name"] in script  # Arabic text is stored as UTF-8, not escaped away
    assert '"direction":"rtl"' in script


def test_status_and_agent_sequence(tmp_path, recorder):
    run_pipeline(make_project(load_requirements("task_manager_en")), tmp_path, recorder)

    assert recorder.steps == [
        ("designing", "software_architect"),
        ("developing", "developer"),
        ("completed", None),
    ]


def test_artifacts_list_only_files_that_exist(tmp_path, recorder):
    project = run_pipeline(make_project(load_requirements("task_manager_en")), tmp_path, recorder)

    by_status = {p["status"]: [a["name"] for a in p["artifacts"]] for p in recorder.saved}
    assert by_status["designing"] == ["requirements.json"]
    assert by_status["developing"] == ["requirements.json", "architecture.json"]
    assert by_status["completed"] == ["requirements.json", "architecture.json", "index.html", "style.css", "app.js"]

    for artifact in project["artifacts"]:
        assert artifact["available"] is True
        assert (tmp_path / artifact["path"]).is_file()


def test_existing_project_fields_are_preserved(tmp_path, recorder):
    original = make_project(load_requirements("task_manager_en"))
    original["feedback"] = "Add a priority field"
    original["answers"] = {"Q-1": "No"}
    before = copy.deepcopy(original)

    project = run_pipeline(original, tmp_path, recorder)

    assert project is original  # updated in place and returned
    changed = {"status", "current_agent", "artifacts", "error"}
    for key, value in before.items():
        if key not in changed:
            assert project[key] == value, key
    assert set(before) <= set(project)


# ---------- rejected input ----------


@pytest.mark.parametrize("approved", [False, None, "yes", 1])
def test_unapproved_project_is_rejected_and_untouched(tmp_path, recorder, approved):
    project = make_project(load_requirements("task_manager_en"), approved=approved)
    before = copy.deepcopy(project)

    with pytest.raises(PipelineNotApproved):
        run_pipeline(project, tmp_path, recorder)

    assert project == before
    assert recorder.saved == []
    assert files_in(tmp_path) == []


def test_project_without_approval_field_is_rejected(tmp_path, recorder):
    project = make_project(load_requirements("task_manager_en"))
    del project["requirements_approved"]

    with pytest.raises(PipelineNotApproved):
        run_pipeline(project, tmp_path, recorder)
    assert recorder.saved == []


@pytest.mark.parametrize(
    "requirements",
    [None, "not a document", [], {}, {"status": "ready_for_review"}],
    ids=["none", "string", "list", "empty", "missing-keys"],
)
def test_missing_or_invalid_requirements_fail(tmp_path, recorder, requirements):
    project = run_pipeline(make_project(requirements), tmp_path, recorder)

    assert project["status"] == "failed"
    assert project["error"]["code"] == "invalid_requirements"
    assert project["error"]["message"]
    assert project["artifacts"] == []
    assert recorder.steps == [("failed", "business_analyst")]  # no agent was started
    assert files_in(tmp_path) == []


@pytest.mark.parametrize("sample", ["vague_idea_en", "out_of_scope_ar"])
def test_requirements_not_ready_for_review_fail(tmp_path, recorder, sample):
    requirements = load_requirements(sample)
    assert requirements["status"] != "ready_for_review"

    project = run_pipeline(make_project(requirements), tmp_path, recorder)

    assert project["status"] == "failed"
    assert project["error"]["code"] == "invalid_requirements"
    assert requirements["status"] in project["error"]["message"]
    assert files_in(tmp_path) == []


def test_malformed_entity_fails_in_architect_stage(tmp_path, recorder):
    requirements = load_requirements("task_manager_en")
    del requirements["entities"][0]["fields"]

    project = run_pipeline(make_project(requirements), tmp_path, recorder)

    assert project["status"] == "failed"
    assert project["error"]["code"] == "architecture_failed"
    assert project["current_agent"] == "software_architect"
    assert "app/app.js" not in files_in(tmp_path)


def test_multi_entity_requirements_are_unsupported(tmp_path, recorder):
    requirements = load_requirements("inventory_manager_ar")
    assert len(requirements["entities"]) == 2

    project = run_pipeline(make_project(requirements), tmp_path, recorder)

    assert project["status"] == "failed"
    assert project["current_agent"] == "software_architect"
    assert project["error"]["code"] == "architecture_unsupported"
    assert "exactly one entity" in project["error"]["message"]
    assert recorder.steps == [("designing", "software_architect"), ("failed", "software_architect")]
    assert recorder.saved[-1]["error"] == project["error"]  # the failure reached storage
    assert files_in(tmp_path) == ["requirements.json"]
    assert [a["name"] for a in project["artifacts"]] == ["requirements.json"]


# ---------- Developer and file system failures ----------


def test_developer_error_fails_the_run(tmp_path, recorder, monkeypatch):
    def broken_generate(requirements, architecture, output_dir):
        raise DeveloperError("Unsupported input: slider")

    monkeypatch.setattr(pipeline, "generate", broken_generate)
    project = run_pipeline(make_project(load_requirements("task_manager_en")), tmp_path, recorder)

    assert project["status"] == "failed"
    assert project["current_agent"] == "developer"
    assert project["error"] == {"code": "generation_failed", "message": "Unsupported input: slider"}
    assert recorder.steps == [
        ("designing", "software_architect"),
        ("developing", "developer"),
        ("failed", "developer"),
    ]
    assert recorder.saved[-1]["error"]["code"] == "generation_failed"
    assert files_in(tmp_path) == ["architecture.json", "requirements.json"]


def test_real_developer_validation_error_fails_the_run(tmp_path, recorder, monkeypatch):
    """The real generate() refuses an architecture it does not support."""
    real_build = pipeline.build_architecture

    def build_with_other_storage(requirements):
        architecture = real_build(requirements)
        architecture["entity"]["storage"]["engine"] = "indexedDB"
        return architecture

    monkeypatch.setattr(pipeline, "build_architecture", build_with_other_storage)
    project = run_pipeline(make_project(load_requirements("task_manager_en")), tmp_path, recorder)

    assert project["status"] == "failed"
    assert project["error"]["code"] == "generation_failed"
    assert "localStorage" in project["error"]["message"]
    assert not (tmp_path / "app").exists()


def test_generation_that_writes_nothing_is_not_completed(tmp_path, recorder, monkeypatch):
    monkeypatch.setattr(pipeline, "generate", lambda requirements, architecture, output_dir: {})
    project = run_pipeline(make_project(load_requirements("task_manager_en")), tmp_path, recorder)

    assert project["status"] == "failed"
    assert project["error"]["code"] == "generation_failed"
    assert "app/index.html" in project["error"]["message"]
    assert "completed" not in [status for status, _ in recorder.steps]


def test_unfilled_template_is_not_completed(tmp_path, recorder, monkeypatch):
    def generate_without_config(requirements, architecture, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        for name in ("index.html", "style.css"):
            (output_dir / name).write_text("x", encoding="utf-8")
        (output_dir / "app.js").write_text("const CONFIG = __BUNYAN_CONFIG__;", encoding="utf-8")

    monkeypatch.setattr(pipeline, "generate", generate_without_config)
    project = run_pipeline(make_project(load_requirements("task_manager_en")), tmp_path, recorder)

    assert project["status"] == "failed"
    assert project["error"]["code"] == "generation_failed"
    assert "placeholder" in project["error"]["message"]


def test_unwritable_workdir_fails_the_run(tmp_path, recorder):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("a file where the project folder should be", encoding="utf-8")

    project = run_pipeline(make_project(load_requirements("task_manager_en")), blocker, recorder)

    assert project["status"] == "failed"
    assert project["error"]["code"] == "storage_failed"
    assert "requirements.json" in project["error"]["message"]
    assert project["artifacts"] == []
    assert recorder.saved[-1]["status"] == "failed"


def test_file_error_while_writing_app_fails_the_run(tmp_path, recorder):
    """app/ cannot be created because a file with that name is in the way."""
    (tmp_path / "app").write_text("blocks the app folder", encoding="utf-8")

    project = run_pipeline(make_project(load_requirements("task_manager_en")), tmp_path, recorder)

    assert project["status"] == "failed"
    assert project["current_agent"] == "developer"
    assert project["error"]["code"] == "storage_failed"
    assert recorder.steps[-1] == ("failed", "developer")
    assert [a["name"] for a in project["artifacts"]] == ["requirements.json", "architecture.json"]
