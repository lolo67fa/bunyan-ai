from typing import List, Dict
from pydantic import BaseModel, Field, field_validator


class ProjectRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value):
        value = value.strip()
        if len(value) < 3 or not any(char.isalpha() for char in value):
            raise ValueError("Idea must contain at least 3 characters and words")
        return value


class ApprovalRequest(BaseModel):
    approved: bool = True
    feedback: str = ""

    @field_validator("feedback")
    @classmethod
    def clean_feedback(cls, value):
        return value.strip()


class AnswersRequest(BaseModel):
    answers: Dict[str, str]


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
