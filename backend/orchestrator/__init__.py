"""BUNYAN AI orchestrator: runs the agents in order for one approved project.

Public API::

    from backend.orchestrator import run_pipeline

    project = run_pipeline(project, workdir, on_update=save_project)
"""

from .pipeline import (
    APP_DIRNAME,
    APP_FILES,
    ARCHITECTURE_FILE,
    REQUIREMENTS_FILE,
    QA_ENV_VAR,
    PipelineNotApproved,
    run_pipeline,
)
from .qa_stage import QA_BLOCKED, QA_FAILED, QA_NOT_RUN, QA_PASSED, TEST_REPORT_FILE

__all__ = [
    "APP_DIRNAME",
    "APP_FILES",
    "ARCHITECTURE_FILE",
    "REQUIREMENTS_FILE",
    "PipelineNotApproved",
    "QA_BLOCKED",
    "QA_ENV_VAR",
    "QA_FAILED",
    "QA_NOT_RUN",
    "QA_PASSED",
    "TEST_REPORT_FILE",
    "run_pipeline",
]
