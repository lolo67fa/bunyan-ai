"""Environment-driven configuration for the Project Manager Agent.

Agent-specific variables (``PM_*``) override the project-wide ones in ``.env``
(``LLM_PROVIDER`` / ``LLM_MODEL``). API keys are read from the environment only
and are never written to output files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
_EFFORTS = {"low", "medium", "high", "xhigh", "max"}


class ConfigError(RuntimeError):
    pass


def load_dotenv_if_available() -> None:
    """Load ``<repo>/.env`` if python-dotenv is installed. Existing variables win."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO_ROOT / ".env", override=False)


def _env(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


@dataclass(frozen=True)
class Settings:
    mode: str                  # "rules" (default, free, deterministic) or "llm"
    provider: Optional[str]
    model: Optional[str]
    effort: str = "medium"
    sdk_max_retries: Optional[int] = None

    def check_llm_ready(self) -> None:
        if self.provider != "anthropic":
            raise ConfigError("LLM mode supports provider 'anthropic' only. Set PM_LLM_PROVIDER or LLM_PROVIDER=anthropic.")
        if not self.model:
            raise ConfigError("Set PM_LLM_MODEL or LLM_MODEL (for example claude-opus-5-5).")
        if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
            raise ConfigError("LLM mode needs ANTHROPIC_API_KEY in your environment or in the git-ignored .env file.")


def get_settings(mode: Optional[str] = None) -> Settings:
    load_dotenv_if_available()
    chosen = (mode or _env("PM_MODE") or "rules").lower()
    if chosen == "mock":  # same word the Business Analyst uses for its free mode
        chosen = "rules"
    if chosen not in ("rules", "llm"):
        raise ConfigError(f"PM_MODE must be 'rules' or 'llm', got '{chosen}'.")
    effort = (_env("PM_EFFORT") or "medium").lower()
    if effort not in _EFFORTS:
        raise ConfigError(f"PM_EFFORT must be one of {sorted(_EFFORTS)}.")
    retries = _env("PM_SDK_MAX_RETRIES")
    model = _env("PM_LLM_MODEL", "LLM_MODEL")
    return Settings(
        mode=chosen,
        provider=(_env("PM_LLM_PROVIDER", "LLM_PROVIDER") or "anthropic").lower(),
        model=model.split("/", 1)[-1] if model else None,
        effort=effort,
        sdk_max_retries=int(retries) if retries else None,
    )
