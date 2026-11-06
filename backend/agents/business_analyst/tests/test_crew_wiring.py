"""CrewAI wiring, built offline. Skipped when CrewAI is not installed (mock-only environments).

Nothing here calls ``crew.kickoff()``, so no request leaves the machine and no API
credit is used. A dummy key is set only because the Anthropic provider checks for
one when it is constructed.
"""

import pytest

from backend.agents.business_analyst.config import Settings
from backend.agents.business_analyst.prompts import EXPECTED_OUTPUT, ROLE, build_task_description

crewai = pytest.importorskip("crewai")

SETTINGS = Settings(mode="llm", provider="anthropic", model="claude-opus-5-5",
                    temperature=0.3, max_retries=0, verbose=False)


@pytest.fixture(autouse=True)
def _dummy_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test-not-a-real-key")


def test_agent_task_and_crew_can_be_built_offline():
    from backend.agents.business_analyst.crew import build_agent, build_task

    agent = build_agent(SETTINGS)
    description = build_task_description("A task manager", "en")
    task = build_task(description, agent)
    crew = crewai.Crew(agents=[agent], tasks=[task], process=crewai.Process.sequential, verbose=False)

    assert agent.role == ROLE and agent.allow_delegation is False
    assert task.expected_output == EXPECTED_OUTPUT
    assert "A task manager" in task.description
    assert crew.tasks == [task]


def test_temperature_is_never_sent_to_anthropic():
    from backend.agents.business_analyst.crew import build_agent

    llm = build_agent(SETTINGS).llm
    assert getattr(llm, "temperature", None) is None
