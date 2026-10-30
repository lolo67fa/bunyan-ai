"""Software Architect Agent (owner: Naifah). Contract: architecture.json v0.2.0-proposal."""

from .from_requirements import ArchitectureError, build_architecture
from .schema import SCHEMA_VERSION, ArchitectureDocument, json_schema

__all__ = ["ArchitectureDocument", "ArchitectureError", "SCHEMA_VERSION", "build_architecture", "json_schema"]
