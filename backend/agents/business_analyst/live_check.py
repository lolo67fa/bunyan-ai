"""One real LLM analysis, for the manual GitHub Actions live test (.github/workflows/ba-live-test.yml).

    python -m backend.agents.business_analyst.live_check --out live-test-output

Exactly one paid model request is allowed:
- the settings must be BA_LLM_BACKEND=direct, BA_MAX_RETRIES=0, BA_FALLBACKS=off and
  BA_SDK_MAX_RETRIES=0, otherwise the script stops before calling anything;
- the generator refuses a second call even if the pipeline asked for one.

Two free calls run first: the Models API checks that the model exists for this key,
and token counting measures the prompt. If either fails, no paid request is made.

The output folder gets summary.json, summary.md and requirements.json (or
raw_output.txt when the answer failed validation). No environment variables or
credentials are written; only whether the API key is present.

Exit codes: 0 all checks passed, 1 the run or a check failed, 2 configuration error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .analyst import AnalysisError, analyze
from .config import ConfigError, Settings, get_settings
from .direct_llm import SYSTEM_PROMPT, build_request, run_direct
from .language import detect_language
from .prompts import build_task_description
from .schema import RequirementsDocument

DEFAULT_IDEA = "أبغى موقع لإدارة المخزون أقدر أضيف فيه المنتجات وأعدل كمياتها وأسعارها وأحذف المنتجات."

# USD per million tokens (Anthropic first-party API). Thinking tokens are billed as output.
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}

REQUEST_TIMEOUT_SECONDS = 900


def single_call_problems(settings: Settings) -> List[str]:
    """Settings that could cause more than one paid request (or no request through the direct backend)."""
    problems = []
    if settings.mode != "llm":
        problems.append("BA_MODE must be llm")
    if settings.provider != "anthropic" or settings.backend != "direct":
        problems.append("use BA_LLM_PROVIDER=anthropic and BA_LLM_BACKEND=direct")
    if settings.max_retries != 0:
        problems.append("BA_MAX_RETRIES must be 0 (no validation retries)")
    if settings.fallbacks:
        problems.append("BA_FALLBACKS must be off (a fallback is a second, billed attempt)")
    if settings.sdk_max_retries != 0:
        problems.append("BA_SDK_MAX_RETRIES must be 0 (no transport retries)")
    return problems


def requirement_checks(doc: RequirementsDocument) -> Dict[str, bool]:
    """What a usable requirements.json must contain (on top of the Pydantic and scope validation)."""
    revalidated = RequirementsDocument.model_validate_json(doc.model_dump_json())
    return {
        "schema_valid": revalidated == doc,
        "language_is_ar": doc.language == "ar",
        "status_ready_for_review": doc.status == "ready_for_review",
        "has_entities": bool(doc.entities),
        "every_entity_has_fields": bool(doc.entities) and all(e.fields for e in doc.entities),
        "has_crud_operations": bool(doc.entities) and all(e.crud.enabled_operations() for e in doc.entities),
        "has_functional_requirements": bool(doc.functional_requirements),
        "has_user_stories": bool(doc.user_stories),
        "has_acceptance_criteria": bool(doc.acceptance_criteria),
    }


def _usage(message: Any) -> Dict[str, Any]:
    usage = getattr(message, "usage", None)
    fields = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    return {f: getattr(usage, f, None) for f in fields}


def _cost(model: str, usage: Dict[str, Any]) -> Optional[float]:
    if model not in PRICES or usage.get("input_tokens") is None or usage.get("output_tokens") is None:
        return None
    price_in, price_out = PRICES[model]
    return round(usage["input_tokens"] * price_in / 1e6 + usage["output_tokens"] * price_out / 1e6, 4)


def run(idea: str, out_dir: Path, client: Any = None, settings: Optional[Settings] = None) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: Dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "idea": idea,
        "api_key_present": bool(os.getenv("ANTHROPIC_API_KEY")),
        "paid_requests": 0,
    }

    def finish(result: str, code: int) -> int:
        summary["result"] = result
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        markdown = _markdown(summary)
        (out_dir / "summary.md").write_text(markdown, encoding="utf-8")
        print(markdown)
        return code

    try:
        settings = settings or get_settings("llm")
        model = build_request("probe", settings)["model"]
    except ConfigError as exc:
        summary["error"] = str(exc)
        return finish("configuration_error", 2)
    summary["settings"] = {"model": model, "backend": settings.backend, "effort": settings.effort,
                           "max_retries": settings.max_retries, "fallbacks": settings.fallbacks,
                           "sdk_max_retries": settings.sdk_max_retries}
    problems = single_call_problems(settings)
    if problems:
        summary["error"] = "; ".join(problems)
        return finish("configuration_error", 2)

    if client is None:
        if not summary["api_key_present"]:
            summary["error"] = "ANTHROPIC_API_KEY is not set"
            return finish("configuration_error", 2)
        import anthropic

        client = anthropic.Anthropic(max_retries=0, timeout=REQUEST_TIMEOUT_SECONDS)

    # Free pre-flight: model availability and prompt size. No paid request if these fail.
    language = detect_language(idea)
    try:
        info = client.models.retrieve(model)
        summary["model_check"] = {"id": info.id, "display_name": getattr(info, "display_name", None)}
        counted = client.messages.count_tokens(
            model=model, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_task_description(idea, language)}],
        )
        summary["prompt_input_tokens"] = counted.input_tokens
    except Exception as exc:  # 401 bad key, 404 unknown model, network
        summary["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        return finish("preflight_failed", 1)

    messages: List[Any] = []

    def one_call(description: str, s: Settings) -> str:
        if summary["paid_requests"]:
            raise RuntimeError("blocked: the test allows exactly one model request")
        summary["paid_requests"] += 1
        return run_direct(description, s, client=client, on_message=messages.append)

    started = time.monotonic()
    doc = None
    try:
        doc = analyze(idea, mode="llm", settings=settings, llm_generator=one_call)
    except AnalysisError as exc:
        summary["validation_errors"] = exc.errors[:50]
        if exc.raw_output:
            (out_dir / "raw_output.txt").write_text(exc.raw_output, encoding="utf-8")
    except Exception as exc:  # API or network error during the paid request
        summary["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
    summary["duration_seconds"] = round(time.monotonic() - started, 1)

    if messages:
        message = messages[0]
        usage = _usage(message)
        summary["response"] = {"model": getattr(message, "model", None), "stop_reason": message.stop_reason,
                               "request_id": getattr(message, "_request_id", None), "usage": usage}
        summary["estimated_cost_usd"] = _cost(model, usage)

    if doc is None:
        return finish("api_error" if "error" in summary else "analysis_failed", 1)

    (out_dir / "requirements.json").write_text(doc.model_dump_json(indent=2) + "\n", encoding="utf-8")
    summary["document"] = {
        "status": doc.status,
        "entities": [{"name": e.name, "fields": [f"{f.name}:{f.type}" for f in e.fields],
                      "crud": e.crud.enabled_operations()} for e in doc.entities],
        "functional_requirements": len(doc.functional_requirements),
        "user_stories": len(doc.user_stories),
        "acceptance_criteria": len(doc.acceptance_criteria),
        "clarification_questions": [{"id": q.id, "blocking": q.blocking} for q in doc.clarification_questions],
        "out_of_scope": [i.category for i in doc.out_of_scope],
    }
    summary["checks"] = requirement_checks(doc)
    passed = all(summary["checks"].values())
    return finish("passed" if passed else "checks_failed", 0 if passed else 1)


def _markdown(s: Dict[str, Any]) -> str:
    lines = ["# Business Analyst live LLM test", "", f"- Result: **{s.get('result')}**",
             f"- Paid model requests: {s.get('paid_requests')}"]
    settings = s.get("settings") or {}
    if settings:
        lines.append(f"- Model: `{settings['model']}` (backend {settings['backend']}, effort {settings['effort']}, "
                     f"validation retries {settings['max_retries']}, fallbacks {settings['fallbacks']}, "
                     f"SDK retries {settings['sdk_max_retries']})")
    if "model_check" in s:
        lines.append(f"- Model available to this key: `{s['model_check']['id']}` ({s['model_check']['display_name']})")
    if "prompt_input_tokens" in s:
        lines.append(f"- Prompt input tokens (counted before the call): {s['prompt_input_tokens']}")
    if "response" in s:
        usage = s["response"]["usage"]
        lines.append(f"- Usage: {usage['input_tokens']} input / {usage['output_tokens']} output tokens; "
                     f"stop reason `{s['response']['stop_reason']}`; request id `{s['response']['request_id']}`")
        lines.append(f"- Estimated cost: ${s.get('estimated_cost_usd')} USD; duration {s.get('duration_seconds')} s")
    if "document" in s:
        d = s["document"]
        lines.append(f"- Status: `{d['status']}`; FR {d['functional_requirements']}, stories {d['user_stories']}, "
                     f"criteria {d['acceptance_criteria']}")
        for e in d["entities"]:
            lines.append(f"  - `{e['name']}`: {', '.join(e['fields'])} | CRUD: {', '.join(e['crud'])}")
    if "checks" in s:
        lines += ["", "| Check | Result |", "|---|---|"]
        lines += [f"| {name} | {'pass' if ok else 'FAIL'} |" for name, ok in s["checks"].items()]
    for key in ("error", "validation_errors"):
        if key in s:
            value = s[key] if isinstance(s[key], str) else "\n".join(f"  - {e}" for e in s[key])
            lines += ["", f"**{key}:**", value]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(prog="python -m backend.agents.business_analyst.live_check")
    parser.add_argument("--idea", default=DEFAULT_IDEA)
    parser.add_argument("--out", type=Path, default=Path("live-test-output"))
    args = parser.parse_args(argv)
    return run(args.idea, args.out)


if __name__ == "__main__":
    sys.exit(main())
