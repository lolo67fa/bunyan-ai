"""Artifacts, preview and download endpoints, on applications really generated
through the API (mock Business Analyst, real Architect and Developer).

Storage points at a temporary folder (conftest.py). No LLM, network or Node.js.
"""

import io
import json
import os
import uuid
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import artifacts, main, storage

TASK_IDEA = "A simple task manager with a title, due date and status"
ARABIC_IDEA = "أبغى تطبيق لإدارة المهام"
SAMPLE_INPUTS = Path(__file__).resolve().parents[1] / "backend" / "agents" / "business_analyst" / "samples" / "inputs"
GENERATED = ["requirements.json", "architecture.json", "index.html", "style.css", "app.js", "project_plan.md", "risks.md"]
NOT_GENERATED_YET = ["test_report.json"]  # QA is switched off in these tests (tests/conftest.py)
ZIP_CONTENTS = [
    "app/app.js", "app/index.html", "app/style.css", "architecture.json", "project_plan.md", "requirements.json", "risks.md",
]


@pytest.fixture
def client():
    return TestClient(main.app)


def create(client, idea=TASK_IDEA):
    response = client.post("/projects", json={"prompt": idea})
    assert response.status_code == 201
    return response.json()


def generate(client, idea=TASK_IDEA):
    """Create and approve a project; returns its id once generation has finished."""
    pid = create(client, idea)["project_id"]
    assert client.post(f"/projects/{pid}/approve", json={"approved": True}).status_code == 200
    assert client.get(f"/projects/{pid}").json()["status"] == "completed"
    return pid


@pytest.fixture
def pid(client):
    return generate(client)


def on_disk(pid, relative):
    return (storage.project_dir(pid) / relative).read_bytes()


# ---------- artifacts ----------


@pytest.mark.parametrize(
    "name, relative, content_type",
    [
        ("requirements.json", "requirements.json", "application/json; charset=utf-8"),
        ("architecture.json", "architecture.json", "application/json; charset=utf-8"),
        ("index.html", "app/index.html", "text/html; charset=utf-8"),
        ("style.css", "app/style.css", "text/css; charset=utf-8"),
        ("app.js", "app/app.js", "text/javascript; charset=utf-8"),
        ("project_plan.md", "project_plan.md", "text/markdown; charset=utf-8"),
        ("risks.md", "risks.md", "text/markdown; charset=utf-8"),
    ],
)
def test_artifact_is_the_generated_file(client, pid, name, relative, content_type):
    response = client.get(f"/projects/{pid}/artifacts/{name}")

    assert response.status_code == 200
    assert response.headers["content-type"] == content_type
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content == on_disk(pid, relative)


def test_json_artifacts_parse_and_match_the_project(client, pid):
    project = client.get(f"/projects/{pid}").json()

    assert client.get(f"/projects/{pid}/artifacts/requirements.json").json() == project["requirements"]
    architecture = client.get(f"/projects/{pid}/artifacts/architecture.json").json()
    assert architecture["entity"]["name"] == project["requirements"]["entities"][0]["name"]
    assert "_mock" not in architecture


def test_project_artifacts_list_matches_what_can_be_fetched(client, pid):
    listed = client.get(f"/projects/{pid}").json()["artifacts"]

    assert [a["name"] for a in listed] == GENERATED
    assert artifacts.available_artifacts(pid) == GENERATED
    for artifact in listed:
        assert artifact["available"] is True
        assert client.get(f'/projects/{pid}/artifacts/{artifact["name"]}').status_code == 200


@pytest.mark.parametrize("name", NOT_GENERATED_YET)
def test_artifacts_that_were_not_produced_are_not_advertised_and_give_404(client, pid, name):
    assert name not in [a["name"] for a in client.get(f"/projects/{pid}").json()["artifacts"]]
    assert client.get(f"/projects/{pid}/artifacts/{name}").status_code == 404


def test_later_artifact_is_served_once_its_file_exists(client, pid):
    """The endpoint needs no change when the QA agent starts writing its report."""
    (storage.project_dir(pid) / "test_report.json").write_text('{"summary": {}}', encoding="utf-8")

    response = client.get(f"/projects/{pid}/artifacts/test_report.json")
    assert response.status_code == 200
    assert response.json() == {"summary": {}}


# ---------- preview ----------


def test_preview_without_slash_redirects_to_canonical_path(client, pid):
    response = client.get(f"/projects/{pid}/preview", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == f"/projects/{pid}/preview/"

    followed = client.get(f"/projects/{pid}/preview")
    assert followed.status_code == 200
    assert str(followed.url).endswith(f"/projects/{pid}/preview/")


def test_preview_serves_the_generated_html(client, pid):
    response = client.get(f"/projects/{pid}/preview/")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.content == on_disk(pid, "app/index.html")
    assert 'href="style.css"' in response.text and 'src="app.js"' in response.text
    assert 'data-testid="btn-add"' in response.text


def test_css_and_js_linked_by_the_html_load_from_the_preview_path(client, pid):
    """index.html links "style.css" and "app.js" relatively: resolve them like a browser."""
    base = f"/projects/{pid}/preview/"

    css = client.get(base + "style.css")
    assert css.status_code == 200
    assert css.headers["content-type"] == "text/css; charset=utf-8"
    assert css.content == on_disk(pid, "app/style.css")

    js = client.get(base + "app.js")
    assert js.status_code == 200
    assert js.headers["content-type"] == "text/javascript; charset=utf-8"
    assert "__BUNYAN_CONFIG__" not in js.text
    assert '"key":"bunyan_task"' in js.text

    assert client.get(base + "index.html").content == on_disk(pid, "app/index.html")


def test_preview_files_carry_the_sandbox_policy(client, pid):
    for path in ("", "style.css", "app.js"):
        headers = client.get(f"/projects/{pid}/preview/{path}").headers
        policy = headers["content-security-policy"]
        assert "default-src 'none'" in policy  # no requests to this API or anywhere else
        assert "script-src 'self'" in policy and "'unsafe-inline'" not in policy
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["cache-control"] == "no-store"
        assert "x-frame-options" not in headers  # the frontend shows the preview in an iframe


def test_arabic_app_preview(client):
    pid = generate(client, ARABIC_IDEA)

    js = client.get(f"/projects/{pid}/preview/app.js")
    assert '"direction":"rtl"' in js.text
    assert js.content == on_disk(pid, "app/app.js")  # UTF-8 bytes unchanged


# ---------- download ----------


def test_download_is_a_valid_zip_with_the_generated_files(client, pid):
    response = client.get(f"/projects/{pid}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == f'attachment; filename="bunyan-app-{pid[:8]}.zip"'

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert archive.testzip() is None
    assert sorted(archive.namelist()) == ZIP_CONTENTS
    for name in ZIP_CONTENTS:
        assert archive.read(name) == on_disk(pid, name)


def test_downloaded_app_is_self_contained(client, pid, tmp_path):
    """Unzipped, app/index.html finds its style.css and app.js next to it."""
    archive = zipfile.ZipFile(io.BytesIO(client.get(f"/projects/{pid}/download").content))
    archive.extractall(tmp_path / "unzipped")

    app = tmp_path / "unzipped" / "app"
    html = (app / "index.html").read_text(encoding="utf-8")
    assert 'href="style.css"' in html and (app / "style.css").is_file()
    assert 'src="app.js"' in html and (app / "app.js").is_file()
    assert json.loads((tmp_path / "unzipped" / "requirements.json").read_text(encoding="utf-8"))["status"] == "ready_for_review"


def test_download_contains_nothing_but_known_artifacts(client, pid, isolated_data_dir):
    folder = storage.project_dir(pid)
    (folder / ".env").write_text("ANTHROPIC_API_KEY=not-a-real-key", encoding="utf-8")
    (folder / "notes.tmp").write_text("temporary", encoding="utf-8")
    (folder / "app" / "extra.js").write_text("// not generated", encoding="utf-8")
    other = generate(client, ARABIC_IDEA)

    archive = zipfile.ZipFile(io.BytesIO(client.get(f"/projects/{pid}/download").content))

    assert sorted(archive.namelist()) == ZIP_CONTENTS
    everything = b"".join(archive.read(n) for n in archive.namelist())
    assert b"not-a-real-key" not in everything
    assert other.encode() not in everything
    assert (isolated_data_dir / f"{pid}.json").is_file()  # the state file exists but is not in the ZIP


def test_download_includes_later_artifacts_when_they_exist(client, pid):
    (storage.project_dir(pid) / "test_report.json").write_text('{"summary": {}}', encoding="utf-8")

    archive = zipfile.ZipFile(io.BytesIO(client.get(f"/projects/{pid}/download").content))
    assert sorted(archive.namelist()) == sorted(ZIP_CONTENTS + ["test_report.json"])


# ---------- missing projects and unfinished work ----------


@pytest.mark.parametrize("path", ["artifacts/app.js", "preview", "preview/", "preview/app.js", "download"])
def test_unknown_project_is_404(client, path):
    response = client.get(f"/projects/{uuid.uuid4()}/{path}", follow_redirects=False)
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


@pytest.mark.parametrize("path", ["artifacts/app.js", "preview/", "download"])
def test_project_id_that_is_not_a_uuid_is_rejected(client, path):
    assert client.get(f"/projects/not-a-uuid/{path}").status_code == 422


def test_project_awaiting_approval_has_nothing_to_serve(client):
    pid = create(client)["project_id"]

    assert client.get(f"/projects/{pid}/artifacts/requirements.json").status_code == 404
    assert client.get(f"/projects/{pid}/artifacts/app.js").status_code == 404
    assert client.get(f"/projects/{pid}/preview/").status_code == 404
    assert client.get(f"/projects/{pid}/preview/app.js").status_code == 404
    response = client.get(f"/projects/{pid}/download")
    assert response.status_code == 404
    assert "not ready" in response.json()["detail"]


def test_failed_project_serves_only_what_was_written(client):
    idea = json.loads((SAMPLE_INPUTS / "inventory_manager_ar.json").read_text(encoding="utf-8"))["idea"]
    pid = create(client, idea)["project_id"]
    client.post(f"/projects/{pid}/approve", json={"approved": True})
    assert client.get(f"/projects/{pid}").json()["status"] == "failed"

    assert client.get(f"/projects/{pid}/artifacts/requirements.json").status_code == 200
    assert client.get(f"/projects/{pid}/artifacts/architecture.json").status_code == 404
    assert client.get(f"/projects/{pid}/preview/").status_code == 404
    response = client.get(f"/projects/{pid}/download")
    assert response.status_code == 404
    assert "architecture.json" in response.json()["detail"] and "app.js" in response.json()["detail"]


def test_download_is_refused_when_a_generated_file_has_gone(client, pid):
    (storage.project_dir(pid) / "app" / "style.css").unlink()

    response = client.get(f"/projects/{pid}/download")
    assert response.status_code == 404
    assert response.json()["detail"].endswith("Missing: style.css")
    assert client.get(f"/projects/{pid}/preview/style.css").status_code == 404
    assert client.get(f"/projects/{pid}/preview/").status_code == 200  # the rest is still there


# ---------- invalid names and path traversal ----------

# Sent over HTTP. A bare ".." is not listed: every HTTP client and browser
# resolves it before sending, so it never reaches the server as a name. The
# lookup function itself is tested with raw names further down.
BAD_NAMES = [
    "%2e%2e",
    "..%2f..%2fmain.py",
    "%2e%2e%2f%2e%2e%2fstorage.py",
    "..%5c..%5cmain.py",
    "app%2fapp.js",
    "app/app.js",
    ".env",
    "app.js.bak",
    "APP.JS",
    "app.js%00.png",
    "secret.txt",
    "{pid}.json",
]


@pytest.mark.parametrize("name", BAD_NAMES)
def test_unknown_and_traversal_artifact_names_are_404(client, pid, isolated_data_dir, name):
    (isolated_data_dir / "secret.txt").write_text("top secret", encoding="utf-8")
    (storage.project_dir(pid) / ".env").write_text("KEY=not-a-real-key", encoding="utf-8")
    name = name.replace("{pid}", pid)

    for prefix in ("artifacts", "preview"):
        response = client.get(f"/projects/{pid}/{prefix}/{name}", follow_redirects=False)
        assert response.status_code == 404, (prefix, name)
        assert b"top secret" not in response.content and b"not-a-real-key" not in response.content


RAW_BAD_NAMES = [
    "..",
    "../secret.txt",
    "../../main.py",
    "..\\secret.txt",
    "app/app.js",
    "app/../../secret.txt",
    "/etc/passwd",
    "",
    ".",
    ".env",
    "requirements.json/",
    "requirements.json\x00",
    "APP.JS",
]


@pytest.mark.parametrize("name", RAW_BAD_NAMES)
def test_lookup_refuses_any_name_outside_the_table(client, pid, isolated_data_dir, name):
    """The functions the endpoints rely on, given names no router would pass through."""
    (isolated_data_dir / "secret.txt").write_text("top secret", encoding="utf-8")

    assert artifacts.artifact_file(pid, name) is None
    assert artifacts.preview_file(pid, name) is None


def test_lookup_refuses_a_project_id_that_is_not_a_uuid(client, pid):
    for bad_id in ("..", f"../{pid}", f"{pid}/../{pid}", ""):
        with pytest.raises(ValueError):
            artifacts.artifact_file(bad_id, "app.js")


def test_preview_serves_app_files_only(client, pid):
    for name in ("requirements.json", "architecture.json"):
        assert client.get(f"/projects/{pid}/artifacts/{name}").status_code == 200
        assert client.get(f"/projects/{pid}/preview/{name}").status_code == 404


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symbolic links are not available on this platform")
def test_symlink_inside_project_folder_is_not_followed(client, pid, isolated_data_dir):
    secret = isolated_data_dir / "secret.txt"
    secret.write_text("top secret", encoding="utf-8")
    target = storage.project_dir(pid) / "test_report.json"
    os.symlink(secret, target)

    assert client.get(f"/projects/{pid}/artifacts/test_report.json").status_code == 404
    archive = zipfile.ZipFile(io.BytesIO(client.get(f"/projects/{pid}/download").content))
    assert "test_report.json" not in archive.namelist()


def test_responses_do_not_reveal_storage_paths(client, pid, isolated_data_dir):
    private = str(isolated_data_dir)
    urls = [
        f"/projects/{pid}",
        f"/projects/{pid}/artifacts/architecture.json",
        f"/projects/{pid}/artifacts/nope",
        f"/projects/{pid}/preview/",
        f"/projects/{pid}/preview/nope",
    ]
    for url in urls:
        response = client.get(url)
        assert private not in response.text, url
        assert private not in json.dumps(dict(response.headers)), url
    assert private.encode() not in client.get(f"/projects/{pid}/download").content


def test_file_system_error_message_has_no_server_path(client, isolated_data_dir):
    pid = create(client)["project_id"]
    (isolated_data_dir / pid).write_text("a file where the project folder should be", encoding="utf-8")

    client.post(f"/projects/{pid}/approve", json={"approved": True})
    project = client.get(f"/projects/{pid}").json()

    assert project["status"] == "failed"
    assert project["error"]["code"] == "storage_failed"
    assert str(isolated_data_dir) not in project["error"]["message"]
    assert str(isolated_data_dir.parent) not in json.dumps(project)


# ---------- isolation between projects ----------


def test_each_project_serves_only_its_own_files(client):
    english = generate(client, TASK_IDEA)
    arabic = generate(client, ARABIC_IDEA)

    en_js = client.get(f"/projects/{english}/preview/app.js").text
    ar_js = client.get(f"/projects/{arabic}/preview/app.js").text
    assert '"language":"en"' in en_js and '"language":"ar"' in ar_js
    assert en_js != ar_js

    for first, second in ((english, arabic), (arabic, english)):
        archive = zipfile.ZipFile(io.BytesIO(client.get(f"/projects/{first}/download").content))
        assert archive.read("app/app.js") == on_disk(first, "app/app.js")
        assert archive.read("app/app.js") != on_disk(second, "app/app.js")
        # Another project's id is never a valid file name inside this one.
        assert client.get(f"/projects/{first}/artifacts/{second}").status_code == 404
        assert client.get(f"/projects/{first}/preview/{second}%2fapp%2fapp.js").status_code == 404


# ---------- nothing else changed ----------


def test_existing_endpoints_still_behave_the_same(client, pid):
    project = client.get(f"/projects/{pid}")
    assert project.status_code == 200 and project.json()["status"] == "completed"
    assert client.post(f"/projects/{pid}/approve", json={"approved": True}).status_code == 409
    assert client.post(f"/projects/{pid}/approve", json={}).status_code == 422
    assert client.post(f"/projects/{pid}/answers", json={"answers": {"Q-1": "x"}}).status_code == 409
    assert client.post("/projects", json={"prompt": ""}).status_code == 422


def test_reading_files_does_not_change_the_project(client, pid):
    before = client.get(f"/projects/{pid}").json()
    for path in ("artifacts/app.js", "preview/", "preview/style.css", "download"):
        client.get(f"/projects/{pid}/{path}")

    assert client.get(f"/projects/{pid}").json() == before
