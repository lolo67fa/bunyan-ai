"""Protected real Business Analyst for a public demo (BUNYAN_LLM_ACCESS=codes).

The public site keeps BA_MODE=mock: anonymous guests never reach a paid model. A guest who
enters an access code (handed out by the project lead) unlocks the real analyst for that
browser session only. Codes are stored as PBKDF2 hashes in BUNYAN_LLM_ACCESS_CODES
("label:pbkdf2:<iterations>:<salt>:<hash>", comma separated; create one with
``python -m backend.security hash-password <label>``).

Spending is bounded four ways, all checked before any request is sent:

- per code: BUNYAN_LLM_MAX_PER_CODE_PER_DAY analyses (default 3);
- the whole site: BUNYAN_MAX_LLM_ANALYSES_PER_DAY analyses and BUNYAN_MAX_CONCURRENT_ANALYSES at once;
- money: BUNYAN_LLM_DAILY_BUDGET_USD (default 2). Each request reserves its worst case
  (BUNYAN_LLM_MAX_INPUT_TOKENS input + BA_MAX_TOKENS output at the model's price) and is then
  settled with the real usage the API reports, so the budget cannot be exceeded even with
  requests in flight;
- per request: one model call (BA_MAX_RETRIES=0, BA_SDK_MAX_RETRIES=0, BA_FALLBACKS=off) with a
  capped output, through the direct Anthropic backend (the only one that reports usage).

Wrong codes are rate-limited per address. Grants expire (BUNYAN_LLM_ACCESS_HOURS, default 12).
State lives in /data/llm_access.json so it survives restarts.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional

from fastapi import HTTPException

from backend import storage

# USD per million tokens (input, output). Same table as the paid live test.
from backend.agents.business_analyst.live_check import PRICES

logger = logging.getLogger("uvicorn.error").getChild("bunyan.llm_access")

STATE_FILE = "llm_access.json"
MAX_FAILURES = 8          # wrong codes per address ...
FAILURE_WINDOW = 900.0    # ... in 15 minutes

_usage_hook: contextvars.ContextVar = contextvars.ContextVar("bunyan_llm_usage_hook", default=None)


def enabled() -> bool:
    value = os.environ.get("BUNYAN_LLM_ACCESS", "off").strip().lower()
    if value not in ("off", "codes"):
        raise RuntimeError("BUNYAN_LLM_ACCESS must be 'off' or 'codes'")
    return value == "codes"


def _float_env(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, default))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0")
    return value


def _int_env(name: str, default: int) -> int:
    return int(_float_env(name, default))


def _codes() -> Dict[str, str]:
    from backend.security import parse_hashed_entries  # same "label:pbkdf2:..." format as BUNYAN_USERS

    return parse_hashed_entries(os.environ.get("BUNYAN_LLM_ACCESS_CODES", ""), "BUNYAN_LLM_ACCESS_CODES")


def _settings():
    from backend.agents.business_analyst.config import get_settings

    return get_settings("llm")


def worst_case_usd() -> float:
    s = _settings()
    price_in, price_out = PRICES[s.model]
    max_in = _int_env("BUNYAN_LLM_MAX_INPUT_TOKENS", 20000)
    return round(max_in * price_in / 1e6 + s.max_tokens * price_out / 1e6, 4)


def check_configuration() -> None:
    """At startup: refuse an unsafe configuration instead of spending money."""
    if not enabled():
        return
    if not _codes():
        raise RuntimeError("BUNYAN_LLM_ACCESS=codes but BUNYAN_LLM_ACCESS_CODES is empty")
    s = _settings()
    s.check_llm_ready()  # provider, model and key
    problems = []
    if s.backend != "direct":
        problems.append("BA_LLM_BACKEND=direct (the only backend that reports token usage)")
    if s.max_retries != 0:
        problems.append("BA_MAX_RETRIES=0")
    if s.sdk_max_retries != 0:
        problems.append("BA_SDK_MAX_RETRIES=0")
    if s.fallbacks:
        problems.append("BA_FALLBACKS=off")
    if s.max_tokens > 32000:
        problems.append("BA_MAX_TOKENS at most 32000")
    if s.model not in PRICES:
        problems.append(f"a model with a known price ({', '.join(PRICES)})")
    if problems:
        raise RuntimeError("BUNYAN_LLM_ACCESS=codes needs " + "; ".join(problems))
    budget = _float_env("BUNYAN_LLM_DAILY_BUDGET_USD", 2.0)
    if worst_case_usd() > budget:
        raise RuntimeError(f"BUNYAN_LLM_DAILY_BUDGET_USD ({budget}) is below the cost of one request "
                           f"in the worst case ({worst_case_usd()} USD)")
    _int_env("BUNYAN_LLM_MAX_PER_CODE_PER_DAY", 3)
    _int_env("BUNYAN_LLM_REPAIRS_PER_CODE_PER_DAY", 3)
    _float_env("BUNYAN_LLM_ACCESS_HOURS", 12)
    logger.info("Protected real analyst: on (model %s, %d codes, %s analyses per code per day, budget %.2f USD per day, "
                "worst case %.2f USD per analysis)", s.model, len(_codes()),
                _int_env("BUNYAN_LLM_MAX_PER_CODE_PER_DAY", 3), budget, worst_case_usd())


@dataclass
class Ticket:
    user: str
    label: str
    reserved_usd: float
    settled: bool = False


class LlmAccess:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: Dict[str, Deque[float]] = defaultdict(deque)
        self._reserved = 0.0

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._reserved = 0.0

    # ----- state -----

    def _read(self) -> Dict[str, Any]:
        today = datetime.now(timezone.utc).date().isoformat()
        path = storage.DATA_DIR / STATE_FILE
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        data.setdefault("grants", {})
        if data.get("date") != today:
            data.update(date=today, per_code={}, spent_usd=0.0, calls=0)
        return data

    def _write(self, data: Dict[str, Any]) -> None:
        path = storage.DATA_DIR / STATE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    # ----- grants -----

    def label_for(self, user: Optional[str]) -> Optional[str]:
        if not user or not enabled():
            return None
        with self._lock:
            grant = self._read()["grants"].get(user)
        if not grant or grant.get("expires", 0) < time.time() or grant.get("label") not in _codes():
            return None  # expired, or the code was removed from the configuration
        return grant["label"]

    def grant(self, user: str, code: str, client: str) -> str:
        from backend.security import _check_password

        if not enabled():
            raise HTTPException(404, "Not found")
        now = time.monotonic()
        with self._lock:
            failures = self._failures[client]
            while failures and now - failures[0] > FAILURE_WINDOW:
                failures.popleft()
            if len(failures) >= MAX_FAILURES:
                raise HTTPException(429, "محاولات كثيرة برموز غير صحيحة. انتظر ربع ساعة ثم حاول مرة أخرى.")
        code = (code or "").strip()
        label = next((name for name, stored in _codes().items() if code and _check_password(code, stored)), None)
        with self._lock:
            if label is None:
                self._failures[client].append(now)
                # Audit without sensitive data: never the code, the session or the address.
                logger.warning("Protected real analyst: wrong access code (%d recent failures from this address)",
                               len(self._failures[client]))
                raise HTTPException(403, "رمز الوصول غير صحيح.")
            data = self._read()
            data["grants"][user] = {"label": label,
                                    "expires": time.time() + _float_env("BUNYAN_LLM_ACCESS_HOURS", 12) * 3600}
            self._write(data)
        logger.info("Protected real analyst: access granted for code '%s'", label)
        return label

    def status(self, user: Optional[str]) -> Dict[str, Any]:
        if not enabled():
            return {"available": False, "enabled": False}
        label = self.label_for(user)
        if label is None:
            return {"available": True, "enabled": False}
        with self._lock:
            used = self._read()["per_code"].get(label, 0)
        return {"available": True, "enabled": True,
                "remaining_today": max(0, _int_env("BUNYAN_LLM_MAX_PER_CODE_PER_DAY", 3) - used)}

    # ----- spending -----

    def reserve(self, user: str, kind: str = "analysis", worst: Optional[float] = None) -> Ticket:
        """Count one paid request (an analysis, or an AI repair) for the user's code and reserve its
        worst-case cost, or raise. All checks and the reservation happen under one lock, so requests
        in parallel cannot pass a limit together."""
        label = self.label_for(user)
        if label is None:
            raise HTTPException(403, "التحليل الحقيقي يحتاج رمز وصول صالحاً.")
        if kind == "repair":
            per_code, counter = _int_env("BUNYAN_LLM_REPAIRS_PER_CODE_PER_DAY", 3), "repairs_per_code"
            limit_message = "استُنفدت محاولات الإصلاح بالذكاء الاصطناعي لهذا الرمز اليوم."
        else:
            per_code, counter = _int_env("BUNYAN_LLM_MAX_PER_CODE_PER_DAY", 3), "per_code"
            limit_message = f"استُخدم هذا الرمز {per_code} مرات اليوم، وهو الحد اليومي. جرّب غداً."
        budget = _float_env("BUNYAN_LLM_DAILY_BUDGET_USD", 2.0)
        worst = worst if worst is not None else worst_case_usd()
        with self._lock:
            data = self._read()
            counts = data.setdefault(counter, {})
            if counts.get(label, 0) >= per_code:
                raise HTTPException(429, limit_message)
            if data["spent_usd"] + self._reserved + worst > budget:
                logger.warning("Protected real analyst: daily budget reached (%.4f spent, %.2f reserved, %.2f budget)",
                               data["spent_usd"], self._reserved, budget)
                raise HTTPException(429, "بلغت ميزانية التحليل الحقيقي لهذا اليوم حدها. جرّب غداً.")
            counts[label] = counts.get(label, 0) + 1
            data["calls"] += 1
            self._reserved += worst
            self._write(data)
        logger.info("Protected real analyst: %s reserved for code '%s' (worst case %.2f USD)", kind, label, worst)
        return Ticket(user, label, worst)

    def settle(self, ticket: Ticket, usage: Optional[Dict[str, Any]], model: Optional[str]) -> float:
        """Replace the reservation with the real cost (the worst case if usage is unknown). Returns the cost."""
        if ticket.settled:
            return 0.0
        cost = ticket.reserved_usd
        if usage and model in PRICES and usage.get("input_tokens") is not None and usage.get("output_tokens") is not None:
            price_in, price_out = PRICES[model]
            cost = round(usage["input_tokens"] * price_in / 1e6 + usage["output_tokens"] * price_out / 1e6, 4)
        with self._lock:
            data = self._read()
            data["spent_usd"] = round(data["spent_usd"] + cost, 4)
            self._reserved = max(0.0, self._reserved - ticket.reserved_usd)
            self._write(data)
            spent = data["spent_usd"]
        ticket.settled = True
        logger.info("Protected real analyst: cost booked for code '%s': %.4f USD (%s); spent today %.4f USD",
                    ticket.label, cost, "real usage" if cost != ticket.reserved_usd else "worst case", spent)
        return cost

    def release_unused(self, ticket: Ticket) -> None:
        """The request never reached the model: give the reservation back (the count stays)."""
        if ticket.settled:
            return
        with self._lock:
            self._reserved = max(0.0, self._reserved - ticket.reserved_usd)
        ticket.settled = True


access = LlmAccess()


class usage_recorder:
    """Context manager around one analysis: settles the ticket with the usage the model call reports."""

    def __init__(self, ticket: Optional[Ticket]):
        self.ticket = ticket
        self.token = None
        self.seen = False

    def __enter__(self):
        if self.ticket is not None:
            self.token = _usage_hook.set(self._on_message)
        return self

    def _on_message(self, message: Any) -> None:
        usage = getattr(message, "usage", None)
        self.seen = True
        access.settle(self.ticket, {"input_tokens": getattr(usage, "input_tokens", None),
                                    "output_tokens": getattr(usage, "output_tokens", None)},
                      getattr(message, "model", None))

    def __exit__(self, *exc):
        if self.ticket is not None:
            _usage_hook.reset(self.token)
            if not self.seen:
                # No message came back. If the request may have been sent, count the worst case.
                access.settle(self.ticket, None, None)
        return False


def usage_hook():
    """The callback for the current analysis, if any (read by direct_llm.run_direct)."""
    return _usage_hook.get()
