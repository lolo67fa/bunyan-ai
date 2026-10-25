"""Environment-driven configuration for the Business Analyst Agent.

Agent-specific variables (``BA_*``) override the project-wide ones from
``.env.example`` (``LLM_PROVIDER`` / ``LLM_MODEL``), so the team can run each
agent on a different model. API keys are only read from the environment and
are never written to output files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]

_API_KEY_VARS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


class ConfigError(RuntimeError):
    pass


def load_dotenv_if_available() -> None:
    """Load ``<repo>/.env`` if python-dotenv is installed. Existing env vars win."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    mode: str                 # "mock" (offline, free) or "llm" (CrewAI + provider API)
    provider: Optional[str]   # e.g. "anthropic", "openai" (any LiteLLM provider prefix)
    model: Optional[str]      # e.g. "claude-sonnet-5-5"
    temperature: float
    max_retries: int          # extra LLM attempts when the output fails validation
    verbose: bool

    @property
    def litellm_model(self) -> str:
        """Model string in the ``provider/model`` form CrewAI (LiteLLM) expects."""
        if not self.provider or not self.model:
            raise ConfigError(
                "LLM mode needs a provider and model. Set BA_LLM_PROVIDER/BA_LLM_MODEL "
                "or LLM_PROVIDER/LLM_MODEL in your .env file."
            )
        if self.model.startswith(f"{self.provider}/"):
            return self.model
        return f"{self.provider}/{self.model}"

    def check_llm_ready(self) -> None:
        self.litellm_model  # raises ConfigError if provider/model missing
        key_var = _API_KEY_VARS.get(self.provider or "")
        if key_var and not os.getenv(key_var):
            raise ConfigError(f"LLM mode with provider '{self.provider}' needs {key_var} in your environment or .env.")


def _env(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def get_settings(mode: Optional[str] = None) -> Settings:
    load_dotenv_if_available()
    resolved_mode = (mode or _env("BA_MODE") or "mock").lower()
    if resolved_mode not in {"mock", "llm"}:
        raise ConfigError(f"BA_MODE must be 'mock' or 'llm', got '{resolved_mode}'")
    provider = _env("BA_LLM_PROVIDER", "LLM_PROVIDER")
    return Settings(
        mode=resolved_mode,
        provider=provider.lower() if provider else None,
        model=_env("BA_LLM_MODEL", "LLM_MODEL"),
        temperature=float(_env("BA_TEMPERATURE") or 0.2),
        max_retries=int(_env("BA_MAX_RETRIES") or 2),
        verbose=(_env("BA_VERBOSE") or "false").lower() in {"1", "true", "yes"},
    )
