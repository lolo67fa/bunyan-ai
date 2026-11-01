
import uuid

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.agents.business_analyst.analyst import analyze


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Store test projects in a temporary folder
    monkeypatch.setattr(main, "save_project", save_project_for_test(tmp_path))
    monkeypatch.setattr(main, "load_project", load_project_for_test(tmp_path))

    return TestClient(main.app)


def save_project_for_test(folder):
    def save(project):
        import json
        file_path = folder / f"{project['project_id']}.json"
        file_path.write_text(
            json.dumps(project, ensure_ascii=False),
            encoding="utf-8"
        )
    return save


def load_project_for_test(folder):
    def load(project_id):
        import json
        file_path = folder / f"{project_id}.json"

        if not file_path.exists():
            return None

        return json.loads(file_path.read_text(encoding="utf-8"))
    return load


def test_create_project(client):
    response = client.post(
        "/projects",
        json={"prompt": "أبغى تطبيق لإدارة المهام"}
    )

    assert response.status_code == 201

    data = response.json()

    assert uuid.UUID(data["project_id"])
    assert data["idea"] == "أبغى تطبيق لإدارة المهام"
    assert data["status"] == "awaiting_approval"
    assert data["requirements"]["status"] == "ready_for_review"


def test_get_project(client):
    created = client.post(
        "/projects",
        json={"prompt": "أبغى تطبيق لإدارة المهام"}
    ).json()

    project_id = created["project_id"]

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 200
    assert response.json()["project_id"] == project_id


def test_project_not_found(client):
    project_id = uuid.uuid4()

    response = client.get(f"/projects/{project_id}")

    assert response.status_code == 404


def test_approve_project(client):
    created = client.post(
        "/projects",
        json={"prompt": "أبغى تطبيق لإدارة المهام"}
    ).json()

    project_id = created["project_id"]

    response = client.post(f"/projects/{project_id}/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["requirements_approved"] is True

    saved = client.get(f"/projects/{project_id}")
    assert saved.json()["status"] == "approved"


def test_cannot_approve_twice(client):
    created = client.post(
        "/projects",
        json={"prompt": "أبغى تطبيق لإدارة المهام"}
    ).json()

    project_id = created["project_id"]

    client.post(f"/projects/{project_id}/approve")
    response = client.post(f"/projects/{project_id}/approve")

    assert response.status_code == 409


def test_invalid_project_id(client):
    response = client.get("/projects/not-a-uuid")

    assert response.status_code == 422
