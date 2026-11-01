
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas.contracts import ProjectRequest
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


@app.post("/projects", status_code=201)
def create_project(data: ProjectRequest):

    project_id = str(uuid.uuid4())

    project = {
        "project_id": project_id,
        "idea": data.prompt,
        "status": "analyzing",
        "current_agent": "business_analyst",
        "requirements": None
    }

    save_project(project)

    try:
        result = analyze(
            idea=data.prompt,
            mode="mock"
        )

        project["requirements"] = result.model_dump(mode="json")

        if result.status == "ready_for_review":
            project["status"] = "awaiting_approval"

        elif result.status == "needs_clarification":
            project["status"] = "awaiting_clarification"

        elif result.status == "rejected_out_of_scope":
            project["status"] = "rejected"

        save_project(project)

    except Exception:
        project["status"] = "failed"
        save_project(project)
        raise HTTPException(
            status_code=500,
            detail="Business Analyst failed"
        )

    return project


@app.get("/projects/{project_id}")
def get_project_pipeline(project_id: uuid.UUID):

    project = load_project(str(project_id))

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return project

@app.post("/projects/{project_id}/approve")
def approve_project(project_id: uuid.UUID):

    project = load_project(str(project_id))

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    if project["status"] != "awaiting_approval":
        raise HTTPException(
            status_code=409,
            detail="Project is not ready for approval"
        )

    project["status"] = "approved"
    project["requirements_approved"] = True

    save_project(project)

    return {
        "project_id": str(project_id),
        "status": project["status"],
        "requirements_approved": True
    }
