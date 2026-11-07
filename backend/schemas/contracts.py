from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ProjectRequest(BaseModel):
    prompt: str

class RequirementModel(BaseModel):
    entity: str
    fields: List[str]
    operations: List[str]

class ArchitectureModel(BaseModel):
    storage: str
    template: str
    screens: List[str]

class TestReportModel(BaseModel):
    passed: int
    failed: int
    success_rate: str
  
