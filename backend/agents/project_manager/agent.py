"""Project Manager Agent: collect the other agents' outputs, write the plan and the risks.

    from backend.agents.project_manager import run_project_manager, write_outputs

    result = run_project_manager({"requirements": req, "architecture": arch,
                                  "test_report": report, "status": "documenting",
                                  "generated_files": ["index.html", "style.css", "app.js"],
                                  "repair_attempt": 1, "run_time_seconds": 62})
    write_outputs(result, "output/<project_id>")   # project_plan.md, risks.md

The agent only reads its inputs and writes its own two documents. It never edits
code or other agents' files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from .config import ConfigError, Settings, get_settings
from .facts import collect
from .llm import LLMStepError, enrich, extra_risks
from .render import build_stages, plan_markdown, risks_markdown, rules_summary
from .risks import build_risks
from .schema import PMInput, PMResult

OUTPUT_FILES = ("project_plan.md", "risks.md")


def run_project_manager(
    data: Union[PMInput, Dict[str, Any]],
    mode: Optional[str] = None,
    settings: Optional[Settings] = None,
    client: Optional[Any] = None,
) -> PMResult:
    pm_input = data if isinstance(data, PMInput) else PMInput.model_validate(data)
    settings = settings or get_settings(mode)
    facts = collect(pm_input)
    stages = build_stages(facts)
    risks = build_risks(facts)
    summary = rules_summary(facts, stages, risks)
    warnings = []
    used_mode = "rules"

    if settings.mode == "llm":
        try:
            settings.check_llm_ready()
            answer = enrich(facts, stages, risks, settings, client)
            summary = answer.summary.strip()
            risks = risks + extra_risks(answer)
            used_mode = "llm"
        except ConfigError:
            raise  # a configuration problem is the user's to fix, not something to hide
        except (LLMStepError, Exception) as exc:  # noqa: BLE001 - any API error falls back to the rules
            warnings.append(f"LLM step skipped, rule-based documents kept: {exc}")

    finished = all(s.status == "done" for s in stages)
    return PMResult(
        mode=used_mode,
        language=facts.language,
        status="complete" if finished else "partial",
        summary=summary,
        stages=stages,
        risks=risks,
        project_plan_md=plan_markdown(facts, stages, risks, summary),
        risks_md=risks_markdown(facts, risks),
        warnings=warnings,
    )


def write_outputs(result: PMResult, out_dir: Union[str, Path]) -> Dict[str, Path]:
    """Write project_plan.md and risks.md (UTF-8) into out_dir and return their paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {"project_plan.md": out / "project_plan.md", "risks.md": out / "risks.md"}
    paths["project_plan.md"].write_text(result.project_plan_md, encoding="utf-8")
    paths["risks.md"].write_text(result.risks_md, encoding="utf-8")
    return paths
