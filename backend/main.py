
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas.contracts import ProjectRequest
from backend.storage import save_project, load_project


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
        "status": "requirements_pending",
        "current_agent": "business_analyst",
        "requirements": None
    }

    save_project(project)

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
