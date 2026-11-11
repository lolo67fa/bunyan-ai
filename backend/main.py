import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response

from backend.schemas.contracts import ProjectRequest, ApprovalRequest, AnswersRequest
from backend.storage import save_project, load_project, project_dir, list_project_ids
from backend import artifacts
from backend.agents.business_analyst.analyst import analyze
from backend.orchestrator import run_pipeline

# Statuses in which the generation pipeline is working on a project.
PIPELINE_STATES = ("designing", "developing", "testing")

# Sent with every generated file. The generated app is untrusted code served
# from the backend's own origin, so the preview may only load its own files:
# no inline scripts, no requests to this API or to any other host.
PREVIEW_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "base-uri 'none'; form-action 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}

# Makes "check the status, then start the pipeline" one step, so two approvals
# sent at the same moment cannot both start a run.
_approval_lock = threading.Lock()
_running_lock = threading.Lock()
_running_projects = set()


@asynccontextmanager
async def lifespan(app):
    recover_interrupted_projects()
    yield


app = FastAPI(title="Bunyan AI Backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def save_with_timestamp(project):
    project["updated_at"] = now_iso()
    save_project(project)


def get_existing_project(project_id):
    project = load_project(str(project_id))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def run_generation(project_id):
    """Background task: Architect -> Developer for one approved project.

    Runs after the approve response has been sent. Every state change is saved
    through save_with_timestamp. Whatever goes wrong, the project ends in
    "completed" or "failed", never stuck in a working status.
    """
    project_id = str(project_id)
    with _running_lock:
        if project_id in _running_projects:
            return
        _running_projects.add(project_id)
    try:
        project = load_project(project_id)
        # Only a project that approve_project just moved to "designing" is run.
        # This also keeps a finished project's files from being generated again.
        if (
            project is None
            or project.get("status") != "designing"
            or project.get("requirements_approved") is not True
        ):
            return
        try:
            run_pipeline(project, project_dir(project_id), save_with_timestamp)
        except Exception as exc:
            project["status"] = "failed"
            project["error"] = {
                "code": "pipeline_failed",
                "message": f"Generation stopped unexpectedly: {type(exc).__name__}: {exc}",
            }
            try:
                save_with_timestamp(project)
            except Exception:
                pass  # storage itself is failing; recover_interrupted_projects handles it on restart
    finally:
        with _running_lock:
            _running_projects.discard(project_id)


def recover_interrupted_projects():
    """Mark runs that were cut off by a server restart as failed.

    Background tasks do not survive a restart, so a project still in a working
    status at startup would otherwise stay there forever.
    """
    recovered = []
    for project_id in list_project_ids():
        project = load_project(project_id)
        if project and project.get("status") in PIPELINE_STATES:
            project["status"] = "failed"
            project["error"] = {
                "code": "pipeline_interrupted",
                "message": "The server restarted while the application was being generated",
            }
            save_with_timestamp(project)
            recovered.append(project_id)
    return recovered


def run_analysis(project, answers=None, feedback=None):
    project["status"] = "analyzing"
    project["current_agent"] = "business_analyst"
    project["error"] = None
    save_with_timestamp(project)
    try:
        result = analyze(
            idea=project["idea"],
            answers=answers,
            feedback=feedback,
            mode="mock",
        )
        project["requirements"] = result.model_dump(mode="json")
        if result.status == "ready_for_review":
            project["status"] = "awaiting_approval"
        elif result.status == "needs_clarification":
            project["status"] = "awaiting_clarification"
        elif result.status == "rejected_out_of_scope":
            project["status"] = "rejected"
        else:
            raise ValueError("Unexpected analyst status")
        save_with_timestamp(project)
    except Exception:
        project["status"] = "failed"
        project["error"] = {"code": "analysis_failed", "message": "Business Analyst failed"}
        save_with_timestamp(project)
        raise HTTPException(status_code=500, detail="Business Analyst failed")
    return project


@app.post("/projects", status_code=201)
def create_project(data: ProjectRequest):
    timestamp = now_iso()
    project = {
        "project_id": str(uuid.uuid4()),
        "idea": data.prompt,
        "status": "analyzing",
        "current_agent": "business_analyst",
        "requirements": None,
        "artifacts": [],
        "repair_attempt": 0,
        "metrics": None,
        "error": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    save_project(project)
    return run_analysis(project)


@app.get("/projects/{project_id}")
def get_project_pipeline(project_id: uuid.UUID):
    return get_existing_project(project_id)


@app.post("/projects/{project_id}/approve")
def approve_project(project_id: uuid.UUID, data: ApprovalRequest, background_tasks: BackgroundTasks):
    with _approval_lock:
        project = get_existing_project(project_id)
        if project["status"] != "awaiting_approval":
            raise HTTPException(status_code=409, detail="Project is not ready for approval")

        if data.approved:
            # Move to "designing" before answering, so a second approval gets 409.
            # The pipeline itself runs after this response has been sent.
            project["status"] = "designing"
            project["current_agent"] = "software_architect"
            project["requirements_approved"] = True
            project["error"] = None
            save_with_timestamp(project)
            background_tasks.add_task(run_generation, project["project_id"])
            return project

    if not data.feedback:
        raise HTTPException(status_code=422, detail="Feedback is required when requesting changes")
    project["requirements_approved"] = False
    project["feedback"] = data.feedback
    return run_analysis(project, answers=project.get("answers"), feedback=data.feedback)

@app.post("/projects/{project_id}/answers")
def submit_answers(project_id: uuid.UUID, data: AnswersRequest):
    project = get_existing_project(project_id)
    if project["status"] != "awaiting_clarification":
        raise HTTPException(status_code=409, detail="Project is not awaiting clarification")
    if not data.answers or not any(value.strip() for value in data.answers.values()):
        raise HTTPException(status_code=422, detail="At least one non-empty answer is required")
    project["answers"] = data.answers
    return run_analysis(project, answers=data.answers)


def file_response(path, name, headers=None):
    return Response(content=path.read_bytes(), media_type=artifacts.media_type(name), headers=headers)


@app.get("/projects/{project_id}/artifacts/{name}")
def get_artifact(project_id: uuid.UUID, name: str):
    """One generated file by its artifact name, e.g. architecture.json or app.js."""
    project = get_existing_project(project_id)
    path = artifacts.artifact_file(project["project_id"], name)
    if path is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return file_response(path, name, {"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})


@app.get("/projects/{project_id}/preview", include_in_schema=False)
def redirect_to_preview(project_id: uuid.UUID):
    """The app links style.css and app.js relatively, so it must be opened at .../preview/."""
    get_existing_project(project_id)
    return RedirectResponse(url=f"/projects/{project_id}/preview/", status_code=307)


@app.get("/projects/{project_id}/preview/")
def preview_app(project_id: uuid.UUID):
    """The generated application's index.html."""
    return preview_app_file(project_id, "index.html")


@app.get("/projects/{project_id}/preview/{filename}")
def preview_app_file(project_id: uuid.UUID, filename: str):
    """A file of the generated application: index.html, style.css or app.js."""
    project = get_existing_project(project_id)
    path = artifacts.preview_file(project["project_id"], filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Preview file not found")
    return file_response(path, filename, PREVIEW_HEADERS)


@app.get("/projects/{project_id}/download")
def download_project(project_id: uuid.UUID):
    """ZIP with the generated application and its requirements and architecture."""
    project = get_existing_project(project_id)
    missing = artifacts.missing_for_download(project["project_id"])
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"The application is not ready for download. Missing: {', '.join(missing)}",
        )
    filename = f"bunyan-app-{str(project_id)[:8]}.zip"
    return Response(
        content=artifacts.build_zip(project["project_id"]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )
