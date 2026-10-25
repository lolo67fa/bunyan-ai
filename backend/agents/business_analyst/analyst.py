"""Business Analyst Agent pipeline.

    idea ──► generator (mock template | CrewAI + LLM) ──► raw JSON text
         ──► parse ──► Pydantic validation ──► scope guard ──► RequirementsDocument

Mock and LLM mode share every step after the generator, so mock runs exercise
the same validation an LLM answer must pass. In LLM mode, a rejected answer is
sent back to the model with the validation errors (``BA_MAX_RETRIES`` times).
"""

from __future__ import annotations

import json
import re
from typing import Callable, Dict, List, Optional

from pydantic import ValidationError

from .config import Settings, get_settings
from .direct_llm import LLMRefusal
from .language import detect_language
from .mock_analyst import mock_generate
from .prompts import build_task_description
from .schema import SCHEMA_VERSION, AnalystInput, RequirementsDocument
from .scope import detect_out_of_scope, find_scope_violations, merge_out_of_scope

Generator = Callable[[str, Settings], str]


class AnalysisError(RuntimeError):
    """The agent could not produce a valid requirements document."""

    def __init__(self, message: str, errors: List[str], raw_output: Optional[str] = None):
        super().__init__(message + "\n" + "\n".join(f"  - {e}" for e in errors))
        self.errors = errors
        self.raw_output = raw_output


class OutputRejected(ValueError):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_json_output(raw: str) -> dict:
    """Extract the JSON object from an LLM answer (tolerates code fences and surrounding text)."""
    text = _FENCE.sub("", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise OutputRejected(["output does not contain a JSON object"])
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise OutputRejected([f"output is not valid JSON: {exc}"]) from exc
    if not isinstance(data, dict):
        raise OutputRejected(["top-level JSON value must be an object"])
    return data


def _format_validation_error(exc: ValidationError) -> List[str]:
    errors = []
    for err in exc.errors():
        location = ".".join(str(p) for p in err["loc"]) or "<document>"
        errors.append(f"{location}: {err['msg']}")
    return errors


def finalize(raw: str, idea: str, language: str, answers: Optional[Dict[str, str]] = None) -> RequirementsDocument:
    """Parse, validate and scope-check a raw answer. Raises ``OutputRejected`` on any problem."""
    data = parse_json_output(raw)
    # Facts the agent is not allowed to change.
    data["schema_version"] = SCHEMA_VERSION
    data["source_idea"] = idea
    data["language"] = language
    try:
        doc = RequirementsDocument.model_validate(data)
    except ValidationError as exc:
        raise OutputRejected(_format_validation_error(exc)) from exc

    violations = find_scope_violations(doc)
    if violations:
        raise OutputRejected(
            [f"{v} - move it to out_of_scope and remove it from the in-scope requirements" for v in violations]
        )

    # The deterministic guard adds anything out-of-scope the analyst forgot to flag.
    user_text = idea + "\n" + "\n".join((answers or {}).values())
    merged = merge_out_of_scope(doc.out_of_scope, detect_out_of_scope(user_text, language))
    if len(merged) != len(doc.out_of_scope):
        doc = RequirementsDocument.model_validate({**doc.model_dump(), "out_of_scope": [m.model_dump() for m in merged]})
    return doc


def _default_llm_generator(description: str, settings: Settings) -> str:
    if settings.backend == "direct":
        from .direct_llm import run_direct

        return run_direct(description, settings)
    from .crew import run_crew

    return run_crew(description, settings)


def analyze(
    idea: str,
    answers: Optional[Dict[str, str]] = None,
    feedback: Optional[str] = None,
    mode: Optional[str] = None,
    settings: Optional[Settings] = None,
    llm_generator: Optional[Generator] = None,
) -> RequirementsDocument:
    """Run the Business Analyst Agent on one idea and return a validated document.

    ``llm_generator`` replaces the CrewAI call (used by tests to simulate LLM answers).
    """
    request = AnalystInput(idea=idea, answers=answers or {}, feedback=feedback)
    settings = settings or get_settings(mode)
    language = detect_language(request.idea)

    if settings.mode == "mock":
        raw = mock_generate(request.idea, language, request.answers)
        try:
            return finalize(raw, request.idea, language, request.answers)
        except OutputRejected as exc:
            raise AnalysisError("mock output failed validation (bug in mock templates)", exc.errors, raw) from exc

    generator = llm_generator or _default_llm_generator
    if llm_generator is None:
        settings.check_llm_ready()
    errors: List[str] = []
    raw: Optional[str] = None
    for _attempt in range(settings.max_retries + 1):
        description = build_task_description(
            request.idea, language, request.answers, request.feedback, errors or None, raw
        )
        try:
            raw = generator(description, settings)
        except LLMRefusal as exc:
            raise AnalysisError("the model did not return a usable answer", [str(exc)], raw) from exc
        try:
            return finalize(raw, request.idea, language, request.answers)
        except OutputRejected as exc:
            errors = exc.errors
    raise AnalysisError(
        f"LLM output was still invalid after {settings.max_retries + 1} attempt(s)", errors, raw
    )


def analyze_input(request: AnalystInput, **kwargs) -> RequirementsDocument:
    return analyze(request.idea, answers=request.answers, feedback=request.feedback, **kwargs)


def validate_requirements_file(text: str) -> RequirementsDocument:
    """Validate an existing requirements.json (schema + scope). Raises ``OutputRejected``."""
    data = parse_json_output(text)
    try:
        doc = RequirementsDocument.model_validate(data)
    except ValidationError as exc:
        raise OutputRejected(_format_validation_error(exc)) from exc
    violations = find_scope_violations(doc)
    if violations:
        raise OutputRejected([str(v) for v in violations])
    return doc
