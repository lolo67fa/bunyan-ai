"""BUNYAN AI — Business Analyst Agent (owner: Ghala Alshreef).

Public API::

    from backend.agents.business_analyst import analyze, RequirementsDocument

    doc = analyze("A simple task manager with due dates", mode="mock")
    doc.model_dump_json(indent=2)
"""

from .analyst import AnalysisError, analyze, analyze_input, validate_requirements_file
from .schema import SCHEMA_VERSION, AnalystInput, RequirementsDocument, json_schema

__all__ = [
    "AnalysisError",
    "AnalystInput",
    "RequirementsDocument",
    "SCHEMA_VERSION",
    "analyze",
    "analyze_input",
    "json_schema",
    "validate_requirements_file",
]
