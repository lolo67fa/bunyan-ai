"""Project storage on disk (git-ignored).

    backend/data/{project_id}.json    project state
    backend/data/{project_id}/        files generated for that project

Project ids are UUIDs. Every path is built from a checked UUID, so an id can
never point outside ``DATA_DIR`` or into another project's folder.
"""

import json
import os
import tempfile
import uuid
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _canonical_id(project_id):
    """Return the id as a canonical UUID string, or raise ValueError."""
    return str(uuid.UUID(str(project_id)))


def project_dir(project_id):
    """Folder for one project's generated files. Not created here."""
    return DATA_DIR / _canonical_id(project_id)


def save_project(project):
    """Write the project state atomically.

    The JSON is written to a temporary file in the same folder and then moved
    over the real file with ``os.replace``. A reader therefore sees either the
    old complete file or the new complete file, never a half-written one.
    """
    project_id = _canonical_id(project["project_id"])
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_path = DATA_DIR / f"{project_id}.json"

    fd, tmp_name = tempfile.mkstemp(dir=str(DATA_DIR), prefix=f".{project_id}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(project, file, ensure_ascii=False, indent=4)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_name, file_path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def load_project(project_id):
    """Return the saved project, or None if the id is unknown or not a UUID."""
    try:
        file_path = DATA_DIR / f"{_canonical_id(project_id)}.json"
    except ValueError:
        return None

    if not file_path.is_file():
        return None

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def list_project_ids():
    """Ids of every saved project."""
    ids = []
    for file_path in sorted(DATA_DIR.glob("*.json")):
        try:
            ids.append(_canonical_id(file_path.stem))
        except ValueError:
            continue
    return ids
