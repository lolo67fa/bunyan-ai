"""API + orchestrator: approving requirements generates the application.

Uses the real storage module (pointed at a temporary folder by conftest.py),
the mock Business Analyst and the real Architect and Developer. No LLM, no
network, no Node.js.

With TestClient, a background task runs after the response is built and before
``client.post`` returns, so the response shows the state at approval time and
the next GET shows the result of the run.
"""

import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import main, storage

TASK_IDEA = "A simple task manager with a title, due date and status"
ARABIC_IDEA = "أبغى تطبيق لإدارة المهام"
SAMPLE_INPUTS = Path(__file__).resolve().parents[1] / "backend" / "agents" / "business_analyst" / "samples" / "inputs"
EXPECTED_FILES = [
    "app/app.js", "app/index.html", "app/style.css", "architecture.json", "project_plan.md", "requirements.json", "risks.md",
]


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def saved_states(monkeypatch):
    """Every project state written to storage, in order."""
    states = []
    real_save = storage.save_project

    def recording_save(project):
        real_save(project)
        states.append(json.loads(json.dumps(project)))

    monkeypatch.setattr(main, "save_project", recording_save)
    return states


def create(client, idea=TASK_IDEA):
    response = client.post("/projects", json={"prompt": idea})
    assert response.status_code == 201
    project = response.json()
    assert project["status"] == "awaiting_approval"
    return project


def approve(client, project_id):
    return client.post(f"/projects/{project_id}/approve", json={"approved": True})


def get(client, project_id):
    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 200
    return response.json()


def files_in(folder):
    return sorted(p.relative_to(folder).as_posix() for p in Path(folder).rglob("*") if p.is_file())


# ---------- success ----------


def test_approval_generates_the_application(client):
    project = create(client)
    pid = project["project_id"]

    response = approve(client, pid)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "designing"
    assert body["current_agent"] == "software_architect"
    assert body["requirements_approved"] is True
    assert body["artifacts"] == []  # nothing had been generated when the response was built

    final = get(client, pid)
    assert final["status"] == "completed"
    assert final["current_agent"] is None
    assert final["error"] is None
    assert [a["name"] for a in final["artifacts"]] == [
        "requirements.json", "architecture.json", "index.html", "style.css", "app.js", "project_plan.md", "risks.md",
    ]
    assert all(a["available"] for a in final["artifacts"])
    assert final["idea"] == project["idea"]
    assert final["requirements"] == project["requirements"]
    assert final["created_at"] == project["created_at"]
    assert final["updated_at"] > body["updated_at"]


def test_five_files_are_stored_in_the_project_folder(client, isolated_data_dir):
    pid = create(client)["project_id"]
    approve(client, pid)

    folder = isolated_data_dir / pid
    assert folder == storage.project_dir(pid)
    assert files_in(folder) == EXPECTED_FILES
    script = (folder / "app" / "app.js").read_text(encoding="utf-8")
    assert "__BUNYAN_CONFIG__" not in script
    assert '"key":"bunyan_task"' in script
    assert json.loads((folder / "requirements.json").read_text(encoding="utf-8")) == get(client, pid)["requirements"]
    # The data folder holds this project's state file and its folder, nothing else.
    assert sorted(p.name for p in isolated_data_dir.iterdir()) == sorted([pid, f"{pid}.json"])


def test_arabic_idea_is_generated(client, isolated_data_dir):
    pid = create(client, ARABIC_IDEA)["project_id"]
    approve(client, pid)

    assert get(client, pid)["status"] == "completed"
    architecture = json.loads((isolated_data_dir / pid / "architecture.json").read_text(encoding="utf-8"))
    assert architecture["app"]["direction"] == "rtl"


def test_state_transitions_are_saved_in_order(client, saved_states):
    pid = create(client)["project_id"]
    del saved_states[:]  # keep only what happens from approval on
    approve(client, pid)

    assert [(s["status"], s["current_agent"]) for s in saved_states] == [
        ("designing", "software_architect"),  # written by the approve endpoint
        ("designing", "software_architect"),  # pipeline: Architect starts
        ("developing", "developer"),
        ("documenting", "project_manager"),
        ("completed", None),
    ]
    stamps = [s["updated_at"] for s in saved_states]
    assert stamps == sorted(stamps)
    assert all(s["requirements_approved"] is True for s in saved_states)


def test_response_is_sent_before_generation_runs(client, monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_generation", lambda project_id: calls.append(project_id))
    pid = create(client)["project_id"]

    response = approve(client, pid)

    assert response.json()["status"] == "designing"
    assert calls == [pid]  # scheduled once as a background task, not run inside the endpoint
    assert get(client, pid)["status"] == "designing"
    assert not storage.project_dir(pid).exists()


def test_two_projects_do_not_share_files(client, isolated_data_dir):
    first = create(client)["project_id"]
    second = create(client, ARABIC_IDEA)["project_id"]
    approve(client, first)
    approve(client, second)

    assert files_in(isolated_data_dir / first) == EXPECTED_FILES
    assert files_in(isolated_data_dir / second) == EXPECTED_FILES
    lang = lambda pid: json.loads((isolated_data_dir / pid / "architecture.json").read_text(encoding="utf-8"))["app"]["language"]
    assert (lang(first), lang(second)) == ("en", "ar")


# ---------- validation is unchanged ----------


@pytest.mark.parametrize(
    "payload",
    [{}, {"approved": "true"}, {"approved": 1}, {"approved": False}, {"approved": True, "extra": 1}],
    ids=["empty", "string", "number", "no-feedback", "extra-field"],
)
def test_invalid_approval_is_422_and_starts_nothing(client, monkeypatch, payload):
    calls = []
    monkeypatch.setattr(main, "run_generation", lambda project_id: calls.append(project_id))
    pid = create(client)["project_id"]

    response = client.post(f"/projects/{pid}/approve", json=payload)

    assert response.status_code == 422
    assert calls == []
    assert get(client, pid)["status"] == "awaiting_approval"
    assert not storage.project_dir(pid).exists()


def test_duplicate_approval_is_409_and_runs_once(client, monkeypatch):
    calls = []
    real = main.run_generation

    def counting(project_id):
        calls.append(project_id)
        real(project_id)

    monkeypatch.setattr(main, "run_generation", counting)
    pid = create(client)["project_id"]

    assert approve(client, pid).status_code == 200
    second = approve(client, pid)

    assert second.status_code == 409
    assert calls == [pid]
    assert get(client, pid)["status"] == "completed"


def test_approval_while_generation_is_pending_is_409(client, monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_generation", lambda project_id: calls.append(project_id))
    pid = create(client)["project_id"]

    assert approve(client, pid).status_code == 200  # project now waits in "designing"
    assert approve(client, pid).status_code == 409
    assert client.post(f"/projects/{pid}/approve", json={"approved": False, "feedback": "Add notes"}).status_code == 409
    assert calls == [pid]


def test_request_changes_does_not_start_generation(client, monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_generation", lambda project_id: calls.append(project_id))
    pid = create(client)["project_id"]

    response = client.post(f"/projects/{pid}/approve", json={"approved": False, "feedback": "Add a notes field"})

    assert response.status_code == 200
    assert response.json()["status"] == "awaiting_approval"
    assert response.json()["requirements_approved"] is False
    assert calls == []
    assert not storage.project_dir(pid).exists()


def test_unknown_project_is_404(client):
    assert approve(client, str(uuid.uuid4())).status_code == 404


# ---------- failures ----------


def test_multi_entity_requirements_end_failed_with_a_clear_error(client, isolated_data_dir, saved_states):
    idea = json.loads((SAMPLE_INPUTS / "inventory_manager_ar.json").read_text(encoding="utf-8"))["idea"]
    project = create(client, idea)
    pid = project["project_id"]
    assert len(project["requirements"]["entities"]) == 2

    assert approve(client, pid).json()["status"] == "designing"
    final = get(client, pid)

    assert final["status"] == "failed"
    assert final["current_agent"] == "software_architect"
    assert final["error"]["code"] == "architecture_unsupported"
    assert "exactly one entity" in final["error"]["message"]
    assert saved_states[-1]["status"] == "failed"
    assert files_in(isolated_data_dir / pid) == ["requirements.json"]
    assert approve(client, pid).status_code == 409  # a failed project is not re-run


def test_unexpected_crash_does_not_leave_project_stuck(client, monkeypatch):
    def crash(project, workdir, on_update):
        raise RuntimeError("disk exploded")

    monkeypatch.setattr(main, "run_pipeline", crash)
    pid = create(client)["project_id"]
    approve(client, pid)

    final = get(client, pid)
    assert final["status"] == "failed"
    assert final["error"]["code"] == "pipeline_failed"
    assert "disk exploded" in final["error"]["message"]


def test_run_generation_ignores_projects_that_are_not_approved_and_designing(client, isolated_data_dir):
    pid = create(client)["project_id"]

    main.run_generation(pid)  # still awaiting approval
    assert get(client, pid)["status"] == "awaiting_approval"
    assert not (isolated_data_dir / pid).exists()

    forged = storage.load_project(pid)
    forged["status"] = "designing"  # status says designing but the user never approved
    storage.save_project(forged)
    main.run_generation(pid)
    assert get(client, pid)["status"] == "designing"
    assert not (isolated_data_dir / pid).exists()

    main.run_generation(str(uuid.uuid4()))  # unknown project: nothing happens


def test_completed_project_is_not_generated_again(client, isolated_data_dir):
    pid = create(client)["project_id"]
    approve(client, pid)
    script = isolated_data_dir / pid / "app" / "app.js"
    script.write_text("// edited after generation", encoding="utf-8")
    before = get(client, pid)

    main.run_generation(pid)

    assert script.read_text(encoding="utf-8") == "// edited after generation"
    assert get(client, pid) == before


def test_interrupted_runs_are_failed_on_startup(client):
    stuck = create(client)["project_id"]
    waiting = create(client)["project_id"]
    done = create(client)["project_id"]
    approve(client, done)
    project = storage.load_project(stuck)
    project.update(status="developing", current_agent="developer", requirements_approved=True)
    storage.save_project(project)

    assert main.recover_interrupted_projects() == [stuck]

    recovered = get(client, stuck)
    assert recovered["status"] == "failed"
    assert recovered["error"]["code"] == "pipeline_interrupted"
    assert recovered["current_agent"] == "developer"
    assert get(client, waiting)["status"] == "awaiting_approval"
    assert get(client, done)["status"] == "completed"


def test_startup_runs_the_recovery(isolated_data_dir):
    project = {"project_id": str(uuid.uuid4()), "status": "designing", "current_agent": "software_architect"}
    storage.save_project(project)

    with TestClient(main.app) as started:  # entering the context runs the startup code
        assert started.get(f'/projects/{project["project_id"]}').json()["status"] == "failed"


# ---------- storage as seen through the API ----------


def test_stored_state_is_valid_json_after_every_update(client, isolated_data_dir, monkeypatch):
    snapshots = []
    real_save = storage.save_project

    def save_and_read_back(project):
        real_save(project)
        file_path = isolated_data_dir / f'{project["project_id"]}.json'
        snapshots.append(json.loads(file_path.read_text(encoding="utf-8"))["status"])

    monkeypatch.setattr(main, "save_project", save_and_read_back)
    pid = create(client)["project_id"]
    approve(client, pid)

    assert snapshots == ["analyzing", "analyzing", "awaiting_approval", "designing", "designing", "developing", "documenting", "completed"]
    assert not list(isolated_data_dir.glob("*.tmp")) and not list(isolated_data_dir.glob(".*"))
