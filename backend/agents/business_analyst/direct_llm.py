"""Direct Anthropic SDK backend (``BA_LLM_BACKEND=direct``).

A lightweight alternative to the CrewAI backend for validating the LLM
integration without installing CrewAI's large dependency tree. It sends the
same task prompt (role, goal and backstory as the system prompt) and returns
the raw text, which then goes through exactly the same parsing, validation,
scope guard and retry loop as a CrewAI answer.

Anthropic models only. Other providers use the CrewAI backend.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .config import ConfigError, Settings
from .prompts import BACKSTORY, EXPECTED_OUTPUT, GOAL, ROLE

SYSTEM_PROMPT = f"You are a {ROLE}.\nGoal: {GOAL}\n{BACKSTORY}\nOutput format: {EXPECTED_OUTPUT}"

# Models that accept the server-side refusal fallback (`fallbacks: "default"`).
_FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

MAX_TOKENS = 64000  # a full requirements document is long; streaming avoids HTTP timeouts


class LLMRefusal(RuntimeError):
    pass


def build_request(description: str, settings: Settings) -> Dict[str, Any]:
    """Request parameters. No temperature/top_p/top_k: the Messages API rejects them (API version 2026-10-21)."""
    if settings.provider != "anthropic":
        raise ConfigError("BA_LLM_BACKEND=direct supports provider 'anthropic' only; use the crewai backend otherwise.")
    model = settings.model.split("/", 1)[-1] if settings.model else None
    if not model:
        raise ConfigError("Set BA_LLM_MODEL or LLM_MODEL (for example claude-opus-5-5).")
    request: Dict[str, Any] = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": description}],
        "output_config": {"effort": settings.effort},
    }
    if model in _FALLBACK_MODELS:
        request["betas"] = [_FALLBACK_BETA]
        request["fallbacks"] = "default"
    return request


def run_direct(description: str, settings: Settings, client: Optional[Any] = None) -> str:
    """Call Claude once and return the text of the answer. ``client`` is injectable for tests."""
    if client is None:
        import anthropic

        client = anthropic.Anthropic()  # credentials from ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN
    with client.beta.messages.stream(**build_request(description, settings)) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        category = getattr(details, "category", None) if details else None
        raise LLMRefusal(f"model refused the request (category: {category}, request id: {message._request_id})")
    if message.stop_reason == "max_tokens":
        raise LLMRefusal(f"answer was cut off at max_tokens={MAX_TOKENS} (request id: {message._request_id})")
    return "".join(block.text for block in message.content if block.type == "text")
