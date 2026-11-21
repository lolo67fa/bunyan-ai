"""Tests for backend/storage.py: atomic writes and per-project folders."""

import json
import threading
import uuid

import pytest

from backend import storage


def new_project(**fields):
    project = {"project_id": str(uuid.uuid4()), "idea": "مدير مهام", "status": "analyzing"}
    project.update(fields)
    return project


def test_save_then_load_round_trip(isolated_data_dir):
    project = new_project()
    storage.save_project(project)

    assert storage.load_project(project["project_id"]) == project
    file_path = isolated_data_dir / f'{project["project_id"]}.json'
    assert json.loads(file_path.read_text(encoding="utf-8")) == project
    assert "مدير مهام" in file_path.read_text(encoding="utf-8")  # Arabic kept readable


def test_save_leaves_no_temporary_files(isolated_data_dir):
    project = new_project()
    for status in ("analyzing", "awaiting_approval", "designing", "developing", "completed"):
        project["status"] = status
        storage.save_project(project)

    assert [p.name for p in isolated_data_dir.iterdir()] == [f'{project["project_id"]}.json']
    assert storage.load_project(project["project_id"])["status"] == "completed"


def test_failed_write_keeps_the_previous_file(isolated_data_dir):
    project = new_project(status="awaiting_approval")
    storage.save_project(project)

    broken = dict(project, status="designing", bad=object())  # not JSON serialisable
    with pytest.raises(TypeError):
        storage.save_project(broken)

    assert storage.load_project(project["project_id"]) == project
    assert [p.name for p in isolated_data_dir.iterdir()] == [f'{project["project_id"]}.json']


def test_reads_during_writes_always_get_valid_json():
    project = new_project(payload="x" * 200_000)
    storage.save_project(project)
    problems = []
    done = threading.Event()

    def reader():
        while not done.is_set():
            try:
                loaded = storage.load_project(project["project_id"])
                if loaded is None or len(loaded["payload"]) != 200_000:
                    problems.append("incomplete project")
            except Exception as exc:  # a half-written file would fail to parse
                problems.append(repr(exc))

    threads = [threading.Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()
    try:
        for n in range(60):
            project["counter"] = n
            storage.save_project(project)
    finally:
        done.set()
        for t in threads:
            t.join()

    assert problems == []
    assert storage.load_project(project["project_id"])["counter"] == 59


@pytest.mark.parametrize("bad_id", ["../secrets", "..", "not-a-uuid", "", "a/b", "/etc/passwd"])
def test_ids_that_are_not_uuids_cannot_reach_files(isolated_data_dir, bad_id):
    assert storage.load_project(bad_id) is None
    with pytest.raises(ValueError):
        storage.project_dir(bad_id)
    with pytest.raises(ValueError):
        storage.save_project({"project_id": bad_id})
    assert list(isolated_data_dir.iterdir()) == []


def test_each_project_gets_its_own_folder_inside_data_dir(isolated_data_dir):
    first, second = str(uuid.uuid4()), str(uuid.uuid4())

    assert storage.project_dir(first) == isolated_data_dir / first
    assert storage.project_dir(first) != storage.project_dir(second)
    assert storage.project_dir(first).parent == isolated_data_dir
    assert storage.project_dir(uuid.UUID(first)) == storage.project_dir(first.upper())


def test_list_project_ids(isolated_data_dir):
    saved = sorted(new_project()["project_id"] for _ in range(3))
    for project_id in saved:
        storage.save_project({"project_id": project_id})
    (isolated_data_dir / "notes.json").write_text("{}", encoding="utf-8")
    (isolated_data_dir / saved[0]).mkdir()  # a project's file folder is not a project

    assert storage.list_project_ids() == saved


def test_unknown_project_is_none():
    assert storage.load_project(str(uuid.uuid4())) is None
