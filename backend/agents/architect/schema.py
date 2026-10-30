"""Provisional ``architecture.json`` contract produced by the Software Architect Agent.

PROPOSAL — NOT YET APPROVED (Naifah, Yara, Alanoud, Sara).

Built to consume the Business Analyst contract ``requirements.json`` v0.1.0-proposal
(``backend/agents/business_analyst/schema.py`` on ``feature/ghala-analyst``):

- Entity and field ``name`` values are copied unchanged from requirements.json.
- Field ``type`` keeps the requirements data type; ``input`` adds the HTML control.
- Validation rule names are identical to requirements.json (``min_value``, ``date_constraint`` ...).

MVP limits (enforced here, see CONTRACT.md):
- exactly ONE entity, no ``reference`` fields;
- exactly two screens, ``list`` and ``form``, in one single-page app;
- full CRUD, inline delete confirmation (no ``window.confirm``).

The Architect decides structure only. No HTML, CSS or ``data-testid`` values live here:
the CRUD template derives testids from field names by fixed rules (CONTRACT.md), so
a model cannot break the fixed QA suite by inventing names.
"""

from __future__ import annotations

from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "0.2.0-proposal"
REQUIREMENTS_SCHEMA_VERSION = "0.1.0-proposal"

FieldType = Literal[
    "string", "text", "integer", "decimal", "boolean", "date", "time", "datetime",
    "email", "phone", "url", "enum",
]  # = requirements FieldType minus "reference" (MVP: one entity)

InputControl = Literal[
    "text", "textarea", "number", "checkbox", "date", "time", "datetime-local",
    "email", "tel", "url", "select",
]

# The only allowed type -> control mapping. The Architect may not pick a different control.
INPUT_FOR_TYPE: dict = {
    "string": "text", "text": "textarea", "integer": "number", "decimal": "number",
    "boolean": "checkbox", "date": "date", "time": "time", "datetime": "datetime-local",
    "email": "email", "phone": "tel", "url": "url", "enum": "select",
}

TEXT_TYPES = {"string", "text", "email", "phone", "url"}
NUMBER_TYPES = {"integer", "decimal"}
DATE_TYPES = {"date", "datetime"}
SEARCHABLE_TYPES = TEXT_TYPES
FILTERABLE_TYPES = {"enum", "boolean", "date"}
SYSTEM_FIELDS = ["id", "created_at", "updated_at"]

ENTITY_NAME_RE = r"^[A-Z][A-Za-z0-9]*$"
FIELD_NAME_RE = r"^[a-z][a-z0-9_]*$"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- entity -------------------------------------------------------------------------------

class ValidationRules(_Model):
    """Same names and meaning as requirements.json ``fields[].validation``."""

    min_length: Optional[int] = Field(default=None, ge=0)
    max_length: Optional[int] = Field(default=None, ge=1)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    date_constraint: Optional[Literal["not_in_past", "not_in_future"]] = None


class Option(_Model):
    value: str = Field(min_length=1, description="Stored value, copied from requirements enum_values.")
    label: str = Field(min_length=1, description="Text shown in the select, in the app language.")


class FieldSpec(_Model):
    name: str = Field(pattern=FIELD_NAME_RE)
    label: str = Field(min_length=1)
    type: FieldType
    input: InputControl
    required: bool
    unique: bool = False
    default: Optional[Union[str, int, float, bool]] = None
    options: Optional[List[Option]] = None
    step: Optional[float] = Field(default=None, gt=0, description="Number inputs only: 1 for integer, 0.01 for decimal.")
    validation: ValidationRules = Field(default_factory=ValidationRules)
    show_in_list: bool

    @model_validator(mode="after")
    def _rules(self) -> "FieldSpec":
        n = self.name
        if n in SYSTEM_FIELDS:
            raise ValueError(f"'{n}' is a system field and must not be listed in fields")
        if self.input != INPUT_FOR_TYPE[self.type]:
            raise ValueError(f"field '{n}': type '{self.type}' requires input '{INPUT_FOR_TYPE[self.type]}', got '{self.input}'")
        if self.type == "enum":
            if not self.options or len(self.options) < 2:
                raise ValueError(f"enum field '{n}' needs at least two options")
            values = [o.value for o in self.options]
            if len(set(values)) != len(values):
                raise ValueError(f"enum field '{n}' has duplicate option values")
            if self.default is not None and self.default not in values:
                raise ValueError(f"default of '{n}' must be one of its option values")
        elif self.options is not None:
            raise ValueError(f"options are only allowed on enum fields ('{n}')")
        if self.type in NUMBER_TYPES:
            if self.step is None:
                raise ValueError(f"number field '{n}' needs step")
        elif self.step is not None:
            raise ValueError(f"step is only allowed on number fields ('{n}')")
        v = self.validation
        if (v.min_length is not None or v.max_length is not None or v.pattern) and self.type not in TEXT_TYPES:
            raise ValueError(f"length/pattern rules are only allowed on text fields ('{n}')")
        if (v.min_value is not None or v.max_value is not None) and self.type not in NUMBER_TYPES:
            raise ValueError(f"min_value/max_value are only allowed on number fields ('{n}')")
        if v.date_constraint and self.type not in DATE_TYPES:
            raise ValueError(f"date_constraint is only allowed on date fields ('{n}')")
        if v.min_length is not None and v.max_length is not None and v.min_length > v.max_length:
            raise ValueError(f"field '{n}': min_length > max_length")
        if v.min_value is not None and v.max_value is not None and v.min_value > v.max_value:
            raise ValueError(f"field '{n}': min_value > max_value")
        return self


class Storage(_Model):
    engine: Literal["localStorage"] = "localStorage"
    key: str = Field(pattern=r"^bunyan_[a-z][a-z0-9_]*$", description="One key holding a JSON array of records.")
    id_field: Literal["id"] = "id"
    id_strategy: Literal["uuid"] = "uuid"
    system_fields: List[Literal["id", "created_at", "updated_at"]] = Field(
        default_factory=lambda: list(SYSTEM_FIELDS),
        description="Added by the generated app to every record; never shown in the form.",
    )


class EntitySpec(_Model):
    name: str = Field(pattern=ENTITY_NAME_RE, description="Copied from requirements entities[].name.")
    label: str = Field(min_length=1)
    plural_label: str = Field(min_length=1)
    display_field: str
    storage: Storage
    fields: List[FieldSpec] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def _refs(self) -> "EntitySpec":
        names = [f.name for f in self.fields]
        if len(set(names)) != len(names):
            raise ValueError(f"entity '{self.name}' has duplicate field names")
        if self.display_field not in names:
            raise ValueError(f"display_field '{self.display_field}' is not a field of '{self.name}'")
        if not any(f.show_in_list for f in self.fields):
            raise ValueError("at least one field must have show_in_list=true")
        return self


# --- screens ------------------------------------------------------------------------------

class Header(_Model):
    type: Literal["header"]


class EmptyState(_Model):
    type: Literal["empty_state"]


class Button(_Model):
    type: Literal["add_button", "save_button", "cancel_button"]
    label: str = Field(min_length=1)


class Search(_Model):
    type: Literal["search"]
    fields: List[str] = Field(min_length=1)
    placeholder: str = Field(min_length=1)


class Filters(_Model):
    type: Literal["filters"]
    fields: List[str] = Field(min_length=1)


class Sort(_Model):
    field: str
    direction: Literal["asc", "desc"] = "asc"


class Table(_Model):
    type: Literal["table"]
    columns: List[str] = Field(min_length=1)
    sort: Optional[Sort] = None
    row_actions: List[Literal["edit", "delete"]] = Field(default_factory=lambda: ["edit", "delete"])


class FormFields(_Model):
    type: Literal["form_fields"]
    fields: List[str] = Field(min_length=1)


Component = Union[Header, EmptyState, Button, Search, Filters, Table, FormFields]


class Screen(_Model):
    id: Literal["list", "form"]
    type: Literal["list", "form"]
    title: str = Field(min_length=1)
    modes: Optional[List[Literal["create", "edit"]]] = None
    components: List[Component] = Field(min_length=1)

    @model_validator(mode="after")
    def _shape(self) -> "Screen":
        if self.id != self.type:
            raise ValueError("screen id must equal its type ('list' or 'form')")
        kinds = [c.type for c in self.components]
        if len(set(kinds)) != len(kinds):
            raise ValueError(f"screen '{self.id}' repeats a component type")
        allowed = {"list": {"header", "add_button", "search", "filters", "table", "empty_state"},
                   "form": {"form_fields", "save_button", "cancel_button"}}[self.type]
        needed = {"list": {"add_button", "table", "empty_state"},
                  "form": {"form_fields", "save_button", "cancel_button"}}[self.type]
        if set(kinds) - allowed:
            raise ValueError(f"screen '{self.id}' cannot contain {sorted(set(kinds) - allowed)}")
        if needed - set(kinds):
            raise ValueError(f"screen '{self.id}' is missing {sorted(needed - set(kinds))}")
        if self.type == "form" and sorted(self.modes or []) != ["create", "edit"]:
            raise ValueError("form screen modes must be ['create', 'edit']")
        if self.type == "list" and self.modes is not None:
            raise ValueError("list screen has no modes")
        return self


# --- navigation, behaviors, messages --------------------------------------------------------

class Transition(_Model):
    from_: Literal["list", "form"] = Field(alias="from")
    event: Literal["add", "edit", "save_success", "cancel"]
    to: Literal["list", "form"]
    mode: Optional[Literal["create", "edit"]] = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Navigation(_Model):
    initial_screen: Literal["list"] = "list"
    transitions: List[Transition]

    @model_validator(mode="after")
    def _complete(self) -> "Navigation":
        events = {t.event for t in self.transitions}
        missing = {"add", "edit", "save_success", "cancel"} - events
        if missing:
            raise ValueError(f"navigation is missing transitions for {sorted(missing)}")
        return self


class Behaviors(_Model):
    validate_before_save: Literal[True] = True
    check_unique_before_save: bool
    prefill_form_on_edit: Literal[True] = True
    load_on_start: Literal[True] = True
    delete_confirmation: Literal["inline", "none"]
    after_save: Literal["show_message_and_return_to_list"] = "show_message_and_return_to_list"
    after_delete: Literal["remove_row_and_show_message"] = "remove_row_and_show_message"


class Messages(_Model):
    """User-facing text. ``{display}`` is replaced at runtime by the record's display_field value."""

    empty: str
    required: str
    invalid: str
    unique: str
    created: str
    updated: str
    deleted: str
    confirm_delete: str
    confirm_button: str
    cancel_delete_button: str
    edit_button: str
    delete_button: str


class DeferredRule(_Model):
    """A requirement the MVP template cannot express. The PM agent records it as a risk."""

    requirement_id: str = Field(pattern=r"^FR-\d+$")
    description: str


class AppInfo(_Model):
    name: str = Field(min_length=1)
    description: str = ""
    language: Literal["ar", "en"]
    direction: Literal["rtl", "ltr"]


class Source(_Model):
    requirements_schema_version: Literal["0.1.0-proposal"] = REQUIREMENTS_SCHEMA_VERSION


class ArchitectureDocument(_Model):
    schema_version: Literal["0.2.0-proposal"] = SCHEMA_VERSION
    source: Source = Field(default_factory=Source)
    app: AppInfo
    entity: EntitySpec
    screens: List[Screen] = Field(min_length=2, max_length=2)
    navigation: Navigation
    behaviors: Behaviors
    messages: Messages
    deferred_rules: List[DeferredRule] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list, description="Gaps the Architect noticed; shown to the PM agent.")

    @model_validator(mode="after")
    def _cross_refs(self) -> "ArchitectureDocument":
        if self.app.direction != ("rtl" if self.app.language == "ar" else "ltr"):
            raise ValueError("direction must be rtl for ar and ltr for en")
        if sorted(s.id for s in self.screens) != ["form", "list"]:
            raise ValueError("screens must be exactly one 'list' and one 'form'")
        fields = {f.name: f for f in self.entity.fields}
        for screen in self.screens:
            for c in screen.components:
                refs = list(getattr(c, "fields", None) or []) + list(getattr(c, "columns", None) or [])
                if isinstance(c, Table) and c.sort:
                    refs.append(c.sort.field)
                unknown = [r for r in refs if r not in fields]
                if unknown:
                    raise ValueError(f"screen '{screen.id}' {c.type} references unknown fields {unknown}")
                if isinstance(c, Search):
                    bad = [r for r in c.fields if fields[r].type not in SEARCHABLE_TYPES]
                    if bad:
                        raise ValueError(f"search only supports text fields, not {bad}")
                if isinstance(c, Filters):
                    bad = [r for r in c.fields if fields[r].type not in FILTERABLE_TYPES]
                    if bad:
                        raise ValueError(f"filters only support enum/boolean/date fields, not {bad}")
                if isinstance(c, FormFields):
                    missing = [f.name for f in self.entity.fields if f.name not in c.fields]
                    if missing:
                        raise ValueError(f"form must include every field; missing {missing}")
        has_unique = any(f.unique for f in self.entity.fields)
        if self.behaviors.check_unique_before_save != has_unique:
            raise ValueError("check_unique_before_save must be true exactly when a field is unique")
        return self


def json_schema() -> dict:
    schema = ArchitectureDocument.model_json_schema(by_alias=True)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "bunyan-ai/architect/architecture.schema.json"
    schema["title"] = "BUNYAN AI architecture.json (PROPOSAL - not yet approved by the team)"
    schema["$comment"] = (
        f"Provisional contract v{SCHEMA_VERSION}. Generated from backend/agents/architect/schema.py; "
        "do not edit by hand. Cross-reference rules are enforced by the Pydantic model only."
    )
    return schema
