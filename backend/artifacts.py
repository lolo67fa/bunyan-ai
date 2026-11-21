"""Read access to the files generated for one project.

Every file is reached through a fixed table of known names, never through a
path taken from the request. A name that is not in the table, a file that has
not been generated, and a file that resolves outside the project's own folder
all give ``None``.
"""

import io
import zipfile
from pathlib import Path

from backend.storage import project_dir

# Artifact name (as the frontend knows it) -> path inside the project folder.
# test_report.json, project_plan.md and risks.md are listed so they are served
# once the QA and Project Manager agents write them; until then they are absent.
ARTIFACT_PATHS = {
    "requirements.json": "requirements.json",
    "architecture.json": "architecture.json",
    "index.html": "app/index.html",
    "style.css": "app/style.css",
    "app.js": "app/app.js",
    "test_report.json": "test_report.json",
    "project_plan.md": "project_plan.md",
    "risks.md": "risks.md",
}

# The generated application: the only files the preview serves.
PREVIEW_FILES = ("index.html", "style.css", "app.js")

# A download is refused unless all of these exist.
REQUIRED_FOR_DOWNLOAD = ("requirements.json", "architecture.json", "index.html", "style.css", "app.js")

MEDIA_TYPES = {
    ".json": "application/json; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
}


def media_type(name):
    return MEDIA_TYPES.get(Path(name).suffix, "application/octet-stream")


def artifact_file(project_id, name):
    """Path of a known artifact that exists for this project, else None."""
    relative = ARTIFACT_PATHS.get(name)
    if relative is None:
        return None
    root = project_dir(project_id).resolve()
    path = (root / relative).resolve()
    # A symlink planted in the folder must not lead anywhere else.
    if root not in path.parents or not path.is_file():
        return None
    return path


def preview_file(project_id, filename):
    """Path of one generated application file, else None."""
    if filename not in PREVIEW_FILES:
        return None
    return artifact_file(project_id, filename)


def available_artifacts(project_id):
    """Names of the artifacts that exist right now, in table order."""
    return [name for name in ARTIFACT_PATHS if artifact_file(project_id, name) is not None]


def missing_for_download(project_id):
    return [name for name in REQUIRED_FOR_DOWNLOAD if artifact_file(project_id, name) is None]


def build_zip(project_id):
    """ZIP bytes holding every existing known artifact, laid out as on disk.

    Only files from the table are added, so nothing else that may sit in the
    data folder (other projects, state files, temporary files) can get in.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, relative in ARTIFACT_PATHS.items():
            path = artifact_file(project_id, name)
            if path is not None:
                archive.writestr(relative, path.read_bytes())
    return buffer.getvalue()
