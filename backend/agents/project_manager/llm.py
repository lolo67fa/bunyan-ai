"""Optional LLM step (``PM_MODE=llm``): an executive summary and up to 3 extra risks.

The model only sees the facts the rules already collected, the stage table and the
rule-based risks. It may not change any number, stage status or existing risk:
its answer is validated, and anything that does not fit is rejected. If the call
or the validation fails, the agent keeps the rule-based documents and records a
warning, so a run never ends without a plan.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any, List, Optional

from pydantic import BaseModel, Field, ValidationError

from .config import Settings
from .facts import Facts
from .schema import Risk, Stage

MAX_TOKENS = 4000

SYSTEM_PROMPT = """You are the Project Manager agent of BUNYAN AI, a platform where five AI agents turn an
idea into a small CRUD web app (requirements, structure, code, tests, delivery).
You write for the person who asked for the app: plain, short, factual.

Rules:
- Use ONLY the facts you are given. Never invent numbers, files, people, dates or features.
- Do not repeat or rename the existing risks; add only risks the facts clearly support.
- Write in the requested language (ar = Modern Standard Arabic, en = English).
- Answer with ONE JSON object and nothing else."""

TASK = """Language: {language}

Facts collected from the other agents:
{facts}

Stage table:
{stages}

Risks already found by the rules:
{risks}

Return JSON with exactly these keys:
{{
  "summary": "2 to 3 sentences: what was built, how far the run got, test result, the most important open risk",
  "additional_risks": [
    {{"title": "...", "likelihood": "low|medium|high", "impact": "low|medium|high",
      "mitigation": "...", "source": "the fact this risk comes from, e.g. requirements.assumptions"}}
  ]
}}
"additional_risks" may be empty and has at most 3 items."""


class _ExtraRisk(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    likelihood: str = Field(..., pattern="^(low|medium|high)$")
    impact: str = Field(..., pattern="^(low|medium|high)$")
    mitigation: str = Field(..., min_length=3, max_length=400)
    source: str = Field(..., min_length=3, max_length=200)


class LLMAnswer(BaseModel):
    summary: str = Field(..., min_length=20, max_length=1200)
    additional_risks: List[_ExtraRisk] = Field(default_factory=list, max_length=3)


class LLMStepError(RuntimeError):
    pass


def build_prompt(facts: Facts, stages: List[Stage], risks: List[Risk]) -> str:
    return TASK.format(
        language=facts.language,
        facts=json.dumps(asdict(facts), ensure_ascii=False, indent=1),
        stages=json.dumps([s.model_dump() for s in stages], ensure_ascii=False),
        risks=json.dumps([r.model_dump() for r in risks], ensure_ascii=False),
    )


def parse_answer(text: str) -> LLMAnswer:
    """Accept a bare JSON object or one inside a ```json fence."""
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = fenced.group(1) if fenced else text[text.find("{"): text.rfind("}") + 1]
    if not raw:
        raise LLMStepError("the answer has no JSON object")
    try:
        return LLMAnswer.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LLMStepError(f"the answer does not match the expected JSON: {exc}") from exc


def call_model(prompt: str, settings: Settings, client: Optional[Any] = None) -> str:
    if client is None:
        import anthropic  # installed from requirements-llm.txt

        options = {} if settings.sdk_max_retries is None else {"max_retries": settings.sdk_max_retries}
        client = anthropic.Anthropic(**options)
    message = client.messages.create(
        model=settings.model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"output_config": {"effort": settings.effort}},
    )
    if getattr(message, "stop_reason", None) == "refusal":
        raise LLMStepError("the model refused the request")
    if getattr(message, "stop_reason", None) == "max_tokens":
        raise LLMStepError(f"the answer was cut off at {MAX_TOKENS} tokens")
    return "".join(getattr(b, "text", "") for b in message.content if getattr(b, "type", "") == "text")


def enrich(facts: Facts, stages: List[Stage], risks: List[Risk], settings: Settings,
           client: Optional[Any] = None) -> LLMAnswer:
    return parse_answer(call_model(build_prompt(facts, stages, risks), settings, client))


def extra_risks(answer: LLMAnswer) -> List[Risk]:
    return [
        Risk(id=f"R-L{i}", title=r.title, likelihood=r.likelihood, impact=r.impact,
             mitigation=r.mitigation, source=f"llm: {r.source}")
        for i, r in enumerate(answer.additional_risks, 1)
    ]
