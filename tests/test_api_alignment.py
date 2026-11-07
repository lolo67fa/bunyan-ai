import uuid
import pytest
from fastapi.testclient import TestClient
from backend import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    projects = {}
    monkeypatch.setattr(main, "save_project", lambda project: projects.update({project["project_id"]: dict(project)}))
    monkeypatch.setattr(main, "load_project", lambda project_id: projects.get(project_id))
    return TestClient(main.app)


def create(client):
    response = client.post("/projects", json={"prompt": "أبغى تطبيق لإدارة المهام"})
    assert response.status_code == 201
    return response.json()


def test_required_fields(client):
    project = create(client)
    assert project["artifacts"] == []
    assert project["repair_attempt"] == 0
    assert project["metrics"] is None
    assert project["error"] is None
    assert project["created_at"]
    assert project["updated_at"]


def test_approve_returns_full_project(client):
    project = create(client)
    response = client.post(f'/projects/{project["project_id"]}/approve', json={"approved": True})
    assert response.status_code == 200
    assert response.json()["idea"] == project["idea"]
    assert response.json()["status"] == "approved"


def test_feedback_reanalysis(client, monkeypatch):
    project = create(client)
    calls = []
    original = main.analyze

    def spy(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(main, "analyze", spy)
    response = client.post(f'/projects/{project["project_id"]}/approve', json={"approved": False, "feedback": "أضف حقل الوصف"})
    assert response.status_code == 200
    assert calls[0]["feedback"] == "أضف حقل الوصف"
    assert response.json()["status"] == "awaiting_approval"


def test_answers_route(client, monkeypatch):
    project = create(client)
    saved = main.load_project(project["project_id"])
    saved["status"] = "awaiting_clarification"
    main.save_project(saved)
    calls = []
    original = main.analyze

    def spy(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(main, "analyze", spy)
    response = client.post(f'/projects/{project["project_id"]}/answers', json={"answers": {"Q-1": "طلاب"}})
    assert response.status_code == 200
    assert calls[0]["answers"] == {"Q-1": "طلاب"}


@pytest.mark.parametrize("idea", ["", "  ", "a", "ab", "12345"])
def test_invalid_idea(client, idea):
    assert client.post("/projects", json={"prompt": idea}).status_code == 422


def test_feedback_required(client):
    project = create(client)
    response = client.post(f'/projects/{project["project_id"]}/approve', json={"approved": False})
    assert response.status_code == 422
