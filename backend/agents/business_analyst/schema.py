"""Provisional requirements contract produced by the Business Analyst Agent.

PROPOSAL — NOT YET APPROVED.
The shared ``requirements`` schema in ``backend/schemas/`` has not been agreed by
the team yet (Ghala, Naifah, Sara, Alanoud). Until it is, this module is the
working contract between the Business Analyst Agent and the Software Architect
Agent. Once the team approves it, it can be moved to ``backend/schemas/``.

Design notes:
- Identifiers (entity names, field names) are always English so the Architect
  and Developer can turn them into code. Human-readable text (labels,
  descriptions, user stories, acceptance criteria) uses the input language.
- System fields (``id``, ``created_at``, ``updated_at``) are NOT listed; the
  Architect/Developer add them to every entity.
- Validators enforce internal consistency (cross references, CRUD coverage,
  measurable acceptance criteria) so that an invalid LLM answer is rejected
  before it reaches the Architect.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "0.1.0-proposal"

CrudOperation = Literal["create", "read", "update", "delete"]
CRUD_OPERATIONS: tuple = ("create", "read", "update", "delete")

FieldType = Literal[
    "string",    # short single-line text
    "text",      # multi-line text
    "integer",
    "decimal",
    "boolean",
    "date",      # YYYY-MM-DD
    "time",      # HH:MM (24h)
    "datetime",  # ISO 8601
    "email",
    "phone",
    "url",
    "enum",      # one of enum_values
    "reference", # id of a record of reference_entity
]

_TEXT_TYPES = {"string", "text", "email", "phone", "url"}
_NUMBER_TYPES = {"integer", "decimal"}
_DATE_TYPES = {"date", "datetime"}
RESERVED_FIELD_NAMES = {"id", "created_at", "updated_at"}

ENTITY_NAME_RE = r"^[A-Z][A-Za-z0-9]*$"
FIELD_NAME_RE = r"^[a-z][a-z0-9_]*$"

# Words that make an acceptance criterion unmeasurable when used in its outcome.
_VAGUE_TERMS_EN = (
    "user-friendly", "user friendly", "easy", "easily", "intuitive", "fast",
    "quickly", "nice", "good", "properly", "appropriate", "efficient", "seamless",
)
_VAGUE_TERMS_AR = ("سهل", "بسهولة", "سريع", "بسرعة", "جميل", "مناسب", "بشكل جيد")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ValidationRules(_Model):
    """Constraints the generated form must enforce for one field."""

    min_length: Optional[int] = Field(default=None, ge=0)
    max_length: Optional[int] = Field(default=None, ge=1)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = Field(default=None, description="JavaScript-compatible regular expression.")
    date_constraint: Optional[Literal["not_in_past", "not_in_future"]] = None

    @model_validator(mode="after")
    def _ranges(self) -> "ValidationRules":
        if self.min_length is not None and self.max_length is not None and self.min_length > self.max_length:
            raise ValueError("min_length must be <= max_length")
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError("min_value must be <= max_value")
        if self.pattern is not None:
            try:
                re.compile(self.pattern)
            except re.error as exc:
                raise ValueError(f"pattern is not a valid regular expression: {exc}") from exc
        return self


class EntityField(_Model):
    name: str = Field(pattern=FIELD_NAME_RE, description="snake_case English identifier.")
    label: str = Field(min_length=1, description="Display label in the input language.")
    type: FieldType
    required: bool
    unique: bool = False
    description: str = ""
    enum_values: Optional[List[str]] = None
    reference_entity: Optional[str] = None
    default: Optional[Any] = None
    validation: ValidationRules = Field(default_factory=ValidationRules)

    @model_validator(mode="after")
    def _type_rules(self) -> "EntityField":
        if self.name in RESERVED_FIELD_NAMES:
            raise ValueError(f"field name '{self.name}' is reserved for system fields")
        if self.type == "enum":
            if not self.enum_values or len(self.enum_values) < 2:
                raise ValueError(f"enum field '{self.name}' needs at least two enum_values")
            if len(set(self.enum_values)) != len(self.enum_values):
                raise ValueError(f"enum field '{self.name}' has duplicate enum_values")
            if self.default is not None and self.default not in self.enum_values:
                raise ValueError(f"default of '{self.name}' must be one of enum_values")
        elif self.enum_values:
            raise ValueError(f"enum_values is only allowed on enum fields ('{self.name}')")
        if self.type == "reference":
            if not self.reference_entity:
                raise ValueError(f"reference field '{self.name}' needs reference_entity")
        elif self.reference_entity:
            raise ValueError(f"reference_entity is only allowed on reference fields ('{self.name}')")

        v = self.validation
        if (v.min_length is not None or v.max_length is not None or v.pattern) and self.type not in _TEXT_TYPES:
            raise ValueError(f"length/pattern rules are only allowed on text fields ('{self.name}')")
        if (v.min_value is not None or v.max_value is not None) and self.type not in _NUMBER_TYPES:
            raise ValueError(f"min_value/max_value are only allowed on numeric fields ('{self.name}')")
        if v.date_constraint and self.type not in _DATE_TYPES:
            raise ValueError(f"date_constraint is only allowed on date fields ('{self.name}')")
        if self.default is not None and self.type != "enum":
            self._check_default()
        return self

    def _check_default(self) -> None:
        """The default must be a value the generated form could save."""
        value, v = self.default, self.validation
        if self.type in _NUMBER_TYPES:
            is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
            if not is_number or (self.type == "integer" and not float(value).is_integer()):
                kind = "an integer" if self.type == "integer" else "a number"
                raise ValueError(f"default of '{self.name}' must be {kind}")
            if (v.min_value is not None and value < v.min_value) or (v.max_value is not None and value > v.max_value):
                raise ValueError(f"default of '{self.name}' is outside its min_value/max_value")
        elif self.type == "boolean":
            if not isinstance(value, bool):
                raise ValueError(f"default of '{self.name}' must be true or false")
        elif self.type == "reference":
            raise ValueError(f"reference field '{self.name}' cannot have a default")
        elif not isinstance(value, str):
            raise ValueError(f"default of '{self.name}' must be a string")


class OperationSpec(_Model):
    enabled: bool
    details: str = ""


class ReadSpec(OperationSpec):
    list_fields: List[str] = Field(default_factory=list, description="Columns shown in the list view.")
    search_fields: List[str] = Field(default_factory=list)
    filter_fields: List[str] = Field(default_factory=list)
    sort_field: Optional[str] = None
    sort_direction: Literal["asc", "desc"] = "asc"


class DeleteSpec(OperationSpec):
    requires_confirmation: bool = True


class CrudSpec(_Model):
    create: OperationSpec
    read: ReadSpec
    update: OperationSpec
    delete: DeleteSpec

    def enabled_operations(self) -> List[str]:
        return [op for op in CRUD_OPERATIONS if getattr(self, op).enabled]


class Entity(_Model):
    name: str = Field(pattern=ENTITY_NAME_RE, description="PascalCase English identifier, singular.")
    label: str = Field(min_length=1)
    plural_label: str = Field(min_length=1)
    description: str = ""
    display_field: str = Field(description="Field used as the record title in lists and confirmations.")
    fields: List[EntityField] = Field(min_length=1)
    crud: CrudSpec

    @model_validator(mode="after")
    def _field_refs(self) -> "Entity":
        names = [f.name for f in self.fields]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise ValueError(f"entity '{self.name}' has duplicate fields: {sorted(dupes)}")
        known = set(names)
        if self.display_field not in known:
            raise ValueError(f"display_field '{self.display_field}' is not a field of '{self.name}'")
        read = self.crud.read
        for attr in ("list_fields", "search_fields", "filter_fields"):
            unknown = [f for f in getattr(read, attr) if f not in known]
            if unknown:
                raise ValueError(f"crud.read.{attr} of '{self.name}' references unknown fields {unknown}")
        if read.sort_field and read.sort_field not in known:
            raise ValueError(f"crud.read.sort_field '{read.sort_field}' is not a field of '{self.name}'")
        if not self.crud.create.enabled or not read.enabled:
            raise ValueError(f"entity '{self.name}' must support at least create and read")
        return self


RequirementCategory = Literal["create", "read", "update", "delete", "validation", "persistence", "other"]


class FunctionalRequirement(_Model):
    id: str = Field(pattern=r"^FR-\d+$")
    entity: Optional[str] = None
    category: RequirementCategory
    description: str = Field(min_length=10)
    priority: Literal["must", "should", "could"] = "must"


class UserStory(_Model):
    id: str = Field(pattern=r"^US-\d+$")
    role: str = Field(min_length=2, description="'As a ...'")
    goal: str = Field(min_length=5, description="'I want to ...'")
    benefit: str = Field(min_length=5, description="'so that ...'")
    entity: Optional[str] = None
    operation: Optional[CrudOperation] = None
    requirement_ids: List[str] = Field(min_length=1)


class AcceptanceCriterion(_Model):
    id: str = Field(pattern=r"^AC-\d+$")
    story_id: str = Field(pattern=r"^US-\d+$")
    category: RequirementCategory
    given: str = Field(min_length=5)
    when: str = Field(min_length=5)
    then: str = Field(min_length=5, description="Observable, testable outcome (used by the QA Agent).")

    @field_validator("then")
    @classmethod
    def _measurable(cls, value: str) -> str:
        lowered = value.lower()
        for term in _VAGUE_TERMS_EN:
            if re.search(rf"\b{re.escape(term)}\b", lowered):
                raise ValueError(f"'then' is not measurable: vague term '{term}'")
        for term in _VAGUE_TERMS_AR:
            if term in value:
                raise ValueError(f"'then' is not measurable: vague term '{term}'")
        return value


class ClarificationQuestion(_Model):
    id: str = Field(pattern=r"^Q-\d+$")
    question: str = Field(min_length=5)
    reason: str = Field(min_length=5)
    blocking: bool = Field(description="True if requirements cannot be finalised without an answer.")
    options: List[str] = Field(default_factory=list)
    suggested_default: Optional[str] = None


OutOfScopeCategory = Literal[
    "authentication",
    "payments",
    "native_mobile",
    "server_backend",
    "realtime_collaboration",
    "enterprise_system",
    "external_integration",
    "file_storage",
    "other",
]


class OutOfScopeItem(_Model):
    feature: str = Field(min_length=2, description="What the user asked for.")
    category: OutOfScopeCategory
    reason: str = Field(min_length=5)
    action: Literal["excluded", "replaced_with_crud_alternative"]
    alternative: Optional[str] = None

    @model_validator(mode="after")
    def _alternative(self) -> "OutOfScopeItem":
        if self.action == "replaced_with_crud_alternative" and not self.alternative:
            raise ValueError("alternative is required when action is 'replaced_with_crud_alternative'")
        return self


class AppInfo(_Model):
    name: str = Field(min_length=2)
    description: str = Field(min_length=10)
    target_users: List[str] = Field(default_factory=list)


Status = Literal["ready_for_review", "needs_clarification", "rejected_out_of_scope"]


class RequirementsDocument(_Model):
    """Top-level ``requirements.json`` document (provisional contract)."""

    schema_version: Literal["0.1.0-proposal"] = SCHEMA_VERSION
    status: Status = Field(
        description=(
            "ready_for_review: complete, awaiting user approval before the Architect runs. "
            "needs_clarification: blocking questions must be answered first. "
            "rejected_out_of_scope: the idea cannot be reduced to a CRUD MVP."
        )
    )
    language: Literal["en", "ar"]
    source_idea: str = Field(min_length=1)
    app: AppInfo
    entities: List[Entity] = Field(default_factory=list)
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list)
    user_stories: List[UserStory] = Field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = Field(default_factory=list)
    clarification_questions: List[ClarificationQuestion] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    out_of_scope: List[OutOfScopeItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistency(self) -> "RequirementsDocument":
        _require_unique("entity name", [e.name for e in self.entities])
        _require_unique("functional requirement id", [r.id for r in self.functional_requirements])
        _require_unique("user story id", [s.id for s in self.user_stories])
        _require_unique("acceptance criterion id", [a.id for a in self.acceptance_criteria])
        _require_unique("clarification question id", [q.id for q in self.clarification_questions])

        entity_names = {e.name for e in self.entities}
        for entity in self.entities:
            for f in entity.fields:
                if f.type == "reference" and f.reference_entity not in entity_names:
                    raise ValueError(
                        f"{entity.name}.{f.name} references unknown entity '{f.reference_entity}'"
                    )
        fr_ids = {r.id for r in self.functional_requirements}
        story_ids = {s.id for s in self.user_stories}
        for r in self.functional_requirements:
            if r.entity is not None and r.entity not in entity_names:
                raise ValueError(f"{r.id} references unknown entity '{r.entity}'")
        fr_entity = {r.id: r.entity for r in self.functional_requirements}
        for s in self.user_stories:
            if s.entity is not None and s.entity not in entity_names:
                raise ValueError(f"{s.id} references unknown entity '{s.entity}'")
            if s.operation is not None and s.entity is None:
                raise ValueError(f"{s.id} has an operation but no entity")
            missing = [rid for rid in s.requirement_ids if rid not in fr_ids]
            if missing:
                raise ValueError(f"{s.id} references unknown requirements {missing}")
            # Requirements without an entity (e.g. persistence) may support any story.
            foreign = [rid for rid in s.requirement_ids if fr_entity[rid] not in (None, s.entity)]
            if s.entity is not None and foreign:
                raise ValueError(f"{s.id} is about '{s.entity}' but references requirements of other entities {foreign}")
        for a in self.acceptance_criteria:
            if a.story_id not in story_ids:
                raise ValueError(f"{a.id} references unknown user story '{a.story_id}'")

        if self.status == "ready_for_review":
            self._check_ready()
        elif self.status == "needs_clarification":
            if not any(q.blocking for q in self.clarification_questions):
                raise ValueError("status 'needs_clarification' requires at least one blocking question")
        elif self.status == "rejected_out_of_scope":
            if not self.out_of_scope:
                raise ValueError("status 'rejected_out_of_scope' requires at least one out_of_scope item")
            # Nothing from a rejected idea may reach the Architect.
            leftovers = [name for name in ("entities", "functional_requirements", "user_stories", "acceptance_criteria")
                         if getattr(self, name)]
            if leftovers:
                raise ValueError(f"status 'rejected_out_of_scope' must not contain {leftovers}")
        return self

    def _check_ready(self) -> None:
        blocking = [q.id for q in self.clarification_questions if q.blocking]
        if blocking:
            raise ValueError(f"status 'ready_for_review' is not allowed with blocking questions {blocking}")
        # An optional question in a finished document must say what was assumed instead.
        undecided = [q.id for q in self.clarification_questions if not q.suggested_default]
        if undecided:
            raise ValueError(f"optional questions {undecided} need a suggested_default in a 'ready_for_review' document")
        if not self.entities:
            raise ValueError("status 'ready_for_review' requires at least one entity")
        if not any(len(e.crud.enabled_operations()) == 4 for e in self.entities):
            raise ValueError("at least one entity must support all four CRUD operations")
        no_columns = [e.name for e in self.entities if not e.crud.read.list_fields]
        if no_columns:
            raise ValueError(f"crud.read.list_fields is empty for {no_columns}; the list view needs columns")
        covered = {(r.entity, r.category) for r in self.functional_requirements}
        for e in self.entities:
            for op in e.crud.enabled_operations():
                if (e.name, op) not in covered:
                    raise ValueError(f"no functional requirement covers '{op}' on entity '{e.name}'")
        stories_with_ac = {a.story_id for a in self.acceptance_criteria}
        for s in self.user_stories:
            if s.id not in stories_with_ac:
                raise ValueError(f"user story {s.id} has no acceptance criteria")
        story_ops = {(s.entity, s.operation) for s in self.user_stories}
        for e in self.entities:
            for op in e.crud.enabled_operations():
                if (e.name, op) not in story_ops:
                    raise ValueError(f"no user story covers '{op}' on entity '{e.name}'")

    # Convenience helpers for downstream agents -------------------------------------------

    def entity(self, name: str) -> Entity:
        for e in self.entities:
            if e.name == name:
                return e
        raise KeyError(name)

    def criteria_for_story(self, story_id: str) -> List[AcceptanceCriterion]:
        return [a for a in self.acceptance_criteria if a.story_id == story_id]


MAX_IDEA_LENGTH = 4000      # the frontend allows 2000; the margin covers other callers
MAX_ANSWERS = 20
MAX_ANSWER_LENGTH = 1000
MAX_FEEDBACK_LENGTH = 2000


class AnalystInput(_Model):
    """Input contract of the Business Analyst Agent (what the orchestrator or CLI passes in).

    ``idea`` is the canonical field name. ``prompt`` is accepted as a deprecated alias
    only because the current FastAPI skeleton (``backend/schemas/contracts.py``) uses it;
    it is mapped to ``idea`` and never appears in the output.
    """

    idea: str = Field(min_length=3, max_length=MAX_IDEA_LENGTH, description="Application idea in Arabic or English.")
    answers: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Answers to earlier clarification questions, keyed by question id (Q-1) or question text. "
            "Blank answers are dropped (treated as unanswered)."
        ),
    )
    feedback: Optional[str] = Field(
        default=None,
        max_length=MAX_FEEDBACK_LENGTH,
        description="User feedback from the approval step; asks the agent to revise.",
    )
    title: Optional[str] = Field(default=None, description="Optional label for sample files; ignored by the agent.")

    @model_validator(mode="before")
    @classmethod
    def _legacy_prompt_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "prompt" in data:
            data = dict(data)
            prompt = data.pop("prompt")
            if "idea" in data and data["idea"] != prompt:
                raise ValueError("send the idea once: 'idea' and the deprecated 'prompt' differ")
            data.setdefault("idea", prompt)
        return data

    @field_validator("idea")
    @classmethod
    def _idea_has_words(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value):
            raise ValueError("idea must describe the application in words (Arabic or English)")
        return value

    @field_validator("answers")
    @classmethod
    def _clean_answers(cls, value: Dict[str, str]) -> Dict[str, str]:
        if len(value) > MAX_ANSWERS:
            raise ValueError(f"at most {MAX_ANSWERS} answers are accepted")
        cleaned: Dict[str, str] = {}
        for key, answer in value.items():
            key, answer = key.strip(), answer.strip()
            if not key:
                raise ValueError("every answer needs a question id (e.g. 'Q-1') or the question text as its key")
            if len(answer) > MAX_ANSWER_LENGTH:
                raise ValueError(f"answer to '{key}' is longer than {MAX_ANSWER_LENGTH} characters")
            if answer:
                cleaned[key] = answer
        return cleaned

    @field_validator("feedback")
    @classmethod
    def _blank_feedback_is_none(cls, value: Optional[str]) -> Optional[str]:
        return value or None


def _require_unique(kind: str, values: List[str]) -> None:
    dupes = sorted({v for v in values if values.count(v) > 1})
    if dupes:
        raise ValueError(f"duplicate {kind}: {dupes}")


def json_schema() -> dict:
    """JSON Schema (draft 2020-12) of the provisional contract, for non-Python consumers."""
    schema = RequirementsDocument.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "bunyan-ai/business-analyst/requirements.schema.json"
    schema["title"] = "BUNYAN AI requirements.json (PROPOSAL - not yet approved by the team)"
    schema["$comment"] = (
        f"Provisional contract v{SCHEMA_VERSION}. Generated from "
        "backend/agents/business_analyst/schema.py; do not edit by hand. "
        "Cross-reference rules (CRUD coverage, story/criterion links) are enforced by the Pydantic model only."
    )
    return schema
