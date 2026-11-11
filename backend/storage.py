
import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def save_project(project):
    project_id = project["project_id"]
    file_path = DATA_DIR / f"{project_id}.json"

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(project, file, ensure_ascii=False, indent=4)


def load_project(project_id):
    file_path = DATA_DIR / f"{project_id}.json"

    if not file_path.is_file():
        return None

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)
