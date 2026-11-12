"""BUNYAN AI — Project Manager Agent (role owner: Jood).

Deterministic: no LLM and no network. It writes ``project_plan.md`` and
``risks.md`` from the data a run really produced.

    from backend.agents.project_manager import write_documents

    write_documents(requirements, architecture, output_dir, qa_report=report, run=project)
"""

from .manager import (
    PLAN_FILE,
    RISKS_FILE,
    ProjectManagerError,
    build_documents,
    write_documents,
)

__all__ = ["PLAN_FILE", "RISKS_FILE", "ProjectManagerError", "build_documents", "write_documents"]
