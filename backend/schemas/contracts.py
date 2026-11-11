from typing import List, Dict
from pydantic import BaseModel, Field, StrictBool, ConfigDict, field_validator, model_validator


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
    model_config = ConfigDict(extra="forbid")

    approved: StrictBool
    feedback: str = ""

    @field_validator("feedback")
    @classmethod
    def clean_feedback(cls, value):
        return value.strip()

    @model_validator(mode="after")
    def validate_feedback(self):
        if not self.approved and len(self.feedback) < 3:
            raise ValueError("Feedback must be at least 3 characters")
        return self




class AnswersRequest(BaseModel):
    answers: Dict[str, str]

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, answers):
        if any(len(value) > 1000 for value in answers.values()):
            raise ValueError("Each answer must be at most 1000 characters")
        return answers


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
