"""Live LLM evaluations: opt-in only, because every run costs API credits.

Enable with:  BA_RUN_LLM_EVALS=1  plus a provider, model and API key (see README).
Without the opt-in every test in this folder is skipped, so a plain `pytest`
run can never spend money.
"""

import os

import pytest

from backend.agents.business_analyst.config import ConfigError, get_settings


def pytest_collection_modifyitems(config, items):
    here = os.path.dirname(__file__)
    eval_items = [i for i in items if str(i.fspath).startswith(here)]
    if not eval_items:
        return
    reason = None
    if os.getenv("BA_RUN_LLM_EVALS") != "1":
        reason = "live LLM evals are opt-in: set BA_RUN_LLM_EVALS=1"
    else:
        try:
            get_settings("llm").check_llm_ready()
        except ConfigError as exc:
            reason = f"LLM not configured: {exc}"
    for item in eval_items:
        item.add_marker(pytest.mark.llm)
        if reason:
            item.add_marker(pytest.mark.skip(reason=reason))
