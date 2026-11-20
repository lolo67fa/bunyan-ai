"""Input and output contract of the Project Manager Agent (PROPOSAL 0.1.0).

The agent reads what the other agents produced and writes two Markdown documents,
``project_plan.md`` and ``risks.md``. It never changes code or other agents' files.

Inputs are read defensively: only ``requirements`` is required, and every other
artifact may be missing (for example when a run stopped early). Unknown fields are
ignored so the agent keeps working while the other contracts are still proposals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = "0.1.0-proposal"

WorkflowStatus = Literal[
    "created", "analyzing", "awaiting_clarification", "awaiting_approval", "rejected", "approved",
    "designing", "developing", "testing", "repairing", "documenting", "completed", "failed",
]


class PMInput(BaseModel):
    """Everything the orchestrator knows about one run when it calls this agent."""

    model_config = ConfigDict(extra="ignore")

    project_id: Optional[str] = None
    status: WorkflowStatus = Field(
        "documenting",
        description="Workflow status when the agent is called. 'documenting' is the normal case.",
    )
    requirements: Dict[str, Any] = Field(..., description="requirements.json (Business Analyst).")
    architecture: Optional[Dict[str, Any]] = Field(None, description="architecture.json (Architect).")
    test_report: Optional[Dict[str, Any]] = Field(None, description="test_report.json (QA Tester), latest run.")
    generated_files: List[str] = Field(
        default_factory=list, description="Files the Developer produced, e.g. index.html, style.css, app.js."
    )
    repair_attempt: int = Field(0, ge=0, le=2, description="Repair attempts used (max 2).")
    run_time_seconds: Optional[float] = Field(None, ge=0, description="Approval to now, whole pipeline.")
    stage_seconds: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional duration per stage: requirements, structure, development, tests, documentation.",
    )
    language: Optional[Literal["ar", "en"]] = Field(
        None, description="Language of the documents. Defaults to requirements.language."
    )

    @field_validator("requirements")
    @classmethod
    def _requirements_shape(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(v.get("app"), dict) or not isinstance(v.get("entities"), list):
            raise ValueError("requirements must contain 'app' and 'entities' (requirements.json from the analyst)")
        return v


Level = Literal["low", "medium", "high"]


class Risk(BaseModel):
    id: str = Field(..., pattern=r"^R-[A-Z]?\d+$")
    title: str = Field(..., min_length=3, max_length=200)
    likelihood: Level
    impact: Level
    mitigation: str = Field(..., min_length=3, max_length=400)
    status: Literal["open", "closed"] = "open"
    source: str = Field(..., description="What the risk is based on, e.g. 'test_report.checks.persist_after_refresh'.")


class Stage(BaseModel):
    key: Literal["requirements", "structure", "development", "tests", "documentation"]
    owner: str
    output: str
    status: Literal["done", "in_progress", "failed", "not_started"]
    seconds: Optional[float] = None


class PMResult(BaseModel):
    """What the agent returns. The two documents are also written as files."""

    schema_version: str = SCHEMA_VERSION
    mode: Literal["rules", "llm"]
    language: Literal["ar", "en"]
    status: Literal["complete", "partial"] = Field(
        ..., description="'partial' when the run stopped before all stages finished."
    )
    summary: str
    stages: List[Stage]
    risks: List[Risk]
    project_plan_md: str
    risks_md: str
    warnings: List[str] = Field(default_factory=list)


def json_schema() -> Dict[str, Any]:
    return {"input": PMInput.model_json_schema(), "output": PMResult.model_json_schema()}
