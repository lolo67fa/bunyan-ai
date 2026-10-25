"""CrewAI wiring for LLM mode.

CrewAI is imported lazily so that mock mode and the offline tests only need
Pydantic. The crew has a single agent and a single task; the orchestrator
(owned by the backend team) can reuse ``build_agent`` / ``build_task`` when it
assembles the full five-agent crew.
"""

from __future__ import annotations

import os

from .config import Settings
from .prompts import BACKSTORY, EXPECTED_OUTPUT, GOAL, ROLE

# Opt out of CrewAI's anonymous telemetry unless the user configured it explicitly.
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")


def build_agent(settings: Settings):
    from crewai import LLM, Agent

    llm = LLM(model=settings.litellm_model, temperature=settings.temperature)
    return Agent(
        role=ROLE,
        goal=GOAL,
        backstory=BACKSTORY,
        llm=llm,
        allow_delegation=False,
        verbose=settings.verbose,
    )


def build_task(description: str, agent):
    from crewai import Task

    return Task(description=description, expected_output=EXPECTED_OUTPUT, agent=agent)


def run_crew(description: str, settings: Settings) -> str:
    """Run the one-agent crew and return the raw text of the answer."""
    from crewai import Crew, Process

    agent = build_agent(settings)
    task = build_task(description, agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=settings.verbose)
    # No `inputs`: the description is already complete and contains JSON braces
    # that CrewAI's {placeholder} interpolation must not touch.
    result = crew.kickoff()
    return result.raw
