"""Shape of test_report.json (proposal 0.1.0), checked with Pydantic."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

CheckStatus = Literal["passed", "failed", "skipped", "not_run"]


class Evidence(BaseModel):
    screenshot: Optional[str] = None
    trace: Optional[str] = None


class CheckError(BaseModel):
    message: str


class Check(BaseModel):
    id: str
    description: str
    status: CheckStatus
    duration_ms: int = Field(ge=0)
    related_criteria: list[str]
    error: Optional[CheckError] = None
    skip_reason: Optional[str] = None
    verbatim_compared: list[dict] = []
    evidence: Evidence


class Summary(BaseModel):
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    not_run: int = Field(ge=0)
    pass_rate: float = Field(ge=0, le=1)
    all_passed: bool


class Run(BaseModel):
    attempt: int = Field(ge=0, le=2)
    max_repair_attempts: int
    started_at: str
    finished_at: str
    duration_ms: int = Field(ge=0)
    browser: str
    blocked_reason: Optional[str] = None


class Defect(BaseModel):
    check_id: str
    message: str
    evidence: Evidence


class QAReport(BaseModel):
    schema_version: str
    entity: Optional[str] = None
    run: Run
    summary: Summary
    checks: list[Check] = Field(min_length=8, max_length=8)
    defects: list[Defect]
    warnings: list[str]

    @model_validator(mode="after")
    def summary_matches_checks(self):
        """The summary must agree with the checks: no invented passes."""
        for status in ("passed", "failed", "skipped", "not_run"):
            real = sum(1 for c in self.checks if c.status == status)
            if getattr(self.summary, status) != real:
                raise ValueError(f"summary.{status} is {getattr(self.summary, status)} but {real} checks are {status}")
        return self