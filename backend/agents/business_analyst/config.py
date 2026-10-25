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

# Any one of these satisfies the credential check for the provider.
_API_KEY_VARS = {"openai": ("OPENAI_API_KEY",), "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
_BACKENDS = {"crewai", "direct"}
_EFFORTS = {"low", "medium", "high", "xhigh", "max"}


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
    model: Optional[str]      # e.g. "claude-opus-5-5"
    temperature: Optional[float]  # only sent when set, and never to Anthropic (the API rejects it)
    max_retries: int          # extra LLM attempts when the output fails validation
    verbose: bool
    backend: str = "crewai"   # "crewai" (default) or "direct" (Anthropic SDK, no CrewAI needed)
    effort: str = "high"      # Anthropic output_config.effort (direct backend)

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
        key_vars = _API_KEY_VARS.get(self.provider or "")
        if key_vars and not any(os.getenv(v) for v in key_vars):
            raise ConfigError(
                f"LLM mode with provider '{self.provider}' needs {' or '.join(key_vars)} "
                "in your environment or in the git-ignored .env file."
            )
        if self.backend == "direct" and self.provider != "anthropic":
            raise ConfigError("BA_LLM_BACKEND=direct supports provider 'anthropic' only.")


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
    backend = (_env("BA_LLM_BACKEND") or "crewai").lower()
    if backend not in _BACKENDS:
        raise ConfigError(f"BA_LLM_BACKEND must be one of {sorted(_BACKENDS)}, got '{backend}'")
    effort = (_env("BA_EFFORT") or "high").lower()
    if effort not in _EFFORTS:
        raise ConfigError(f"BA_EFFORT must be one of {sorted(_EFFORTS)}, got '{effort}'")
    temperature = _env("BA_TEMPERATURE")
    return Settings(
        mode=resolved_mode,
        provider=provider.lower() if provider else None,
        model=_env("BA_LLM_MODEL", "LLM_MODEL"),
        temperature=float(temperature) if temperature else None,
        max_retries=int(_env("BA_MAX_RETRIES") or 2),
        verbose=(_env("BA_VERBOSE") or "false").lower() in {"1", "true", "yes"},
        backend=backend,
        effort=effort,
    )
