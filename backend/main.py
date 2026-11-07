from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.schemas.contracts import ProjectRequest

app = FastAPI(title="Bunyan AI Backend - Mock Pipeline")

# السماح للواجهة الأمامية بالاتصال بالـ Backend بدون قيود
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/projects")
def create_project(data: ProjectRequest):
    return {
        "project_id": "bunyan-demo-01",
        "status": "requirements_pending",
        "requirements": {
            "entity": "مهمة (Task)",
            "fields": ["العنوان", "الوصف", "الحالة"],
            "operations": ["Create", "Read", "Update", "Delete"]
        }
    }

@app.get("/projects/{project_id}")
def get_project_pipeline(project_id: str):
    return {
        "project_id": project_id,
        "status": "completed",
        "architecture": {"storage": "localStorage", "template": "CRUD-Fixed"},
        "test_report": {"passed": 8, "failed": 0, "success_rate": "100%"}
    }
