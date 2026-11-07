import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas.contracts import ProjectRequest, ApprovalRequest, AnswersRequest
from backend.storage import save_project, load_project
from backend.agents.business_analyst.analyst import analyze

app = FastAPI(title="Bunyan AI Backend")
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
def approve_project(project_id: uuid.UUID, data: ApprovalRequest):
    project = get_existing_project(project_id)
    if project["status"] != "awaiting_approval":
        raise HTTPException(status_code=409, detail="Project is not ready for approval")

    if data.approved:
        project["status"] = "approved"
        project["requirements_approved"] = True
        save_with_timestamp(project)
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
