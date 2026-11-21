"""Cumulative (lifetime) budget for every protected Anthropic request: analyses and AI repairs.

``BUNYAN_TOTAL_LLM_BUDGET_USD`` (for example ``5.00``) is the total for the whole experiment. It is
never reset: not at midnight, not on restart or redeployment, not for new guest sessions and not
when access codes change. It is an extra limit next to the daily ones in ``llm_access.py``.

Accounting is in integer micro-dollars (1 USD = 1,000,000), never floats.

The ledger is ``/data/llm_budget.json`` on the persistent volume, with a sentinel file
``/data/llm_budget.initialized``. It is created once, and only when both of these are set:

- ``BUNYAN_TOTAL_LLM_BUDGET_USD``: the total;
- ``BUNYAN_LLM_BUDGET_STARTING_SPENT_USD``: what was already spent before the ledger existed
  (historical paid tests, decided by the project lead). There is no default: without it, nothing
  is created and every paid request is refused.

**Fail closed:** after creation, a missing, unreadable or corrupted ledger, a missing sentinel next
to an existing ledger, or a total in the environment that differs from the ledger's total, blocks
every paid request until a person fixes it. The ledger is never recreated silently: the sentinel
stays, so a deleted ledger is refused.

For each request: the worst-case cost is reserved under a lock before the request and written to
disk; afterwards the reservation is replaced by the real cost from the API's usage. When the cost is
unknown (timeout, connection error, crash), the worst case is booked. A reservation left over by a
previous process (crash or redeploy mid-request) is booked at its worst case on the next start.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from typing import Any, Dict, Optional

from backend import storage

LEDGER_FILE = "llm_budget.json"
SENTINEL_FILE = "llm_budget.initialized"
MICRO = 1_000_000
MAX_ENTRIES = 500  # recent entries kept in the ledger for the admin summary


class BudgetError(RuntimeError):
    """The cumulative budget cannot be used (not set up, corrupted, or exhausted)."""

    def __init__(self, message: str, user_message: str, status: int = 503):
        super().__init__(message)
        self.user_message = user_message
        self.status = status


def usd_to_micro(value: Any) -> int:
    """'5.00' -> 5_000_000. Rounds fractions of a micro-dollar up (never under-counts)."""
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"not an amount: {value!r}") from exc
    if not d.is_finite() or d < 0:
        raise ValueError(f"not an amount: {value!r}")
    return int((d * MICRO).to_integral_value(rounding=ROUND_CEILING))


def micro_to_usd(micro: int) -> str:
    return f"{Decimal(micro) / MICRO:.6f}"


def configured() -> bool:
    return bool(os.environ.get("BUNYAN_TOTAL_LLM_BUDGET_USD", "").strip())


class Ledger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._recovered = False

    def reset(self) -> None:  # tests only: forget in-process state
        with self._lock:
            self._recovered = False

    # ----- files -----

    def _paths(self):
        return storage.DATA_DIR / LEDGER_FILE, storage.DATA_DIR / SENTINEL_FILE

    def _load(self) -> Dict[str, Any]:
        """The ledger, validated, or BudgetError. Creates it only on the very first, explicit setup."""
        if not configured():
            raise BudgetError("BUNYAN_TOTAL_LLM_BUDGET_USD is not set",
                              "التحليل الحقيقي غير مفعّل: لم تُحدَّد الميزانية الإجمالية.")
        path, sentinel = self._paths()
        try:
            total_env = usd_to_micro(os.environ["BUNYAN_TOTAL_LLM_BUDGET_USD"])
        except ValueError as exc:
            raise BudgetError(str(exc), "إعداد الميزانية الإجمالية غير صالح.") from exc
        if not path.exists():
            if sentinel.exists():
                raise BudgetError("the budget ledger is missing but was initialised before: refusing to recreate it",
                                  "سجل الميزانية مفقود؛ أُوقف التحليل الحقيقي حتى يُراجَع.")
            start = os.environ.get("BUNYAN_LLM_BUDGET_STARTING_SPENT_USD", "").strip()
            if not start:
                raise BudgetError("BUNYAN_LLM_BUDGET_STARTING_SPENT_USD is not set: the starting balance must be decided",
                                  "التحليل الحقيقي غير مفعّل: لم يُحدَّد الرصيد الابتدائي للميزانية.")
            try:
                start_micro = usd_to_micro(start)
            except ValueError as exc:
                raise BudgetError(str(exc), "إعداد الميزانية الإجمالية غير صالح.") from exc
            data = {"version": 1, "total_micro": total_env, "spent_micro": start_micro,
                    "starting_spent_micro": start_micro, "reserved": {}, "per_label": {},
                    "created_at": time.time(), "entries": [{"at": time.time(), "kind": "start",
                                                            "label": None, "micro": start_micro}]}
            self._write(data)
            sentinel.write_text("The cumulative LLM budget ledger was initialised. Do not delete.\n", encoding="utf-8")
            self._recovered = True  # a new ledger has no reservations from an earlier process
            return data
        if not sentinel.exists():
            raise BudgetError("the budget sentinel is missing next to an existing ledger",
                              "سجل الميزانية غير مكتمل؛ أُوقف التحليل الحقيقي حتى يُراجَع.")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ok = (isinstance(data, dict) and data.get("version") == 1
                  and all(isinstance(data.get(k), int) and data[k] >= 0 for k in ("total_micro", "spent_micro"))
                  and isinstance(data.get("reserved"), dict) and isinstance(data.get("per_label"), dict)
                  and all(isinstance(v, dict) and isinstance(v.get("micro"), int) for v in data["reserved"].values()))
        except (OSError, ValueError):
            ok = False
        if not ok:
            raise BudgetError("the budget ledger is unreadable or corrupted",
                              "سجل الميزانية تالف؛ أُوقف التحليل الحقيقي حتى يُراجَع.")
        if data["total_micro"] != total_env:
            raise BudgetError(f"BUNYAN_TOTAL_LLM_BUDGET_USD ({micro_to_usd(total_env)}) differs from the ledger's total "
                              f"({micro_to_usd(data['total_micro'])}); change the ledger deliberately, not the variable",
                              "إعداد الميزانية لا يطابق السجل؛ أُوقف التحليل الحقيقي حتى يُراجَع.")
        if not self._recovered:
            # Reservations left by an earlier process: the request may have been billed. Book the worst case.
            for rid, r in list(data["reserved"].items()):
                data["spent_micro"] += r["micro"]
                data["entries"].append({"at": time.time(), "kind": "recovered", "label": r.get("label"),
                                        "micro": r["micro"], "note": "reservation from an earlier run, worst case"})
                del data["reserved"][rid]
            self._recovered = True
            self._write(data)
        return data

    def _write(self, data: Dict[str, Any]) -> None:
        path, _ = self._paths()
        data["entries"] = data["entries"][-MAX_ENTRIES:]
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        os.replace(tmp, path)

    # ----- operations -----

    def check(self) -> None:
        """Raise BudgetError if paid requests cannot be made now (used at startup and for status)."""
        with self._lock:
            self._load()

    def reserve(self, label: str, kind: str, worst_micro: int, per_label_limit: Optional[int] = None) -> str:
        """Reserve the worst case, or raise BudgetError. Atomic: one lock, written before returning."""
        with self._lock:
            data = self._load()
            used = data["spent_micro"] + sum(r["micro"] for r in data["reserved"].values())
            if used + worst_micro > data["total_micro"]:
                raise BudgetError(f"cumulative budget exhausted ({micro_to_usd(used)} of {micro_to_usd(data['total_micro'])})",
                                  "انتهت الميزانية الإجمالية للتجربة؛ لا يمكن إجراء تحليل حقيقي آخر.", 429)
            counts = data["per_label"].setdefault(label, {})
            if per_label_limit is not None and counts.get(kind, 0) >= per_label_limit:
                raise BudgetError(f"access code '{label}' used its {per_label_limit} {kind}s for the experiment",
                                  "استُخدم هذا الرمز للحد الأقصى المسموح في التجربة.", 429)
            counts[kind] = counts.get(kind, 0) + 1
            rid = uuid.uuid4().hex
            data["reserved"][rid] = {"micro": worst_micro, "label": label, "kind": kind, "at": time.time()}
            self._write(data)
            return rid

    def settle(self, rid: str, actual_micro: Optional[int]) -> int:
        """Replace a reservation by the real cost; the worst case when the cost is unknown. Returns the booked cost."""
        with self._lock:
            data = self._load()
            r = data["reserved"].pop(rid, None)
            if r is None:
                return 0
            booked = r["micro"] if actual_micro is None else int(actual_micro)
            data["spent_micro"] += booked
            data["entries"].append({"at": time.time(), "kind": r["kind"], "label": r["label"], "micro": booked,
                                    "note": "real usage" if actual_micro is not None else "worst case (cost unknown)"})
            self._write(data)
            return booked

    def release_unsent(self, rid: str) -> None:
        """Only for a request that certainly never reached the API (it was refused before sending)."""
        with self._lock:
            data = self._load()
            r = data["reserved"].pop(rid, None)
            if r is not None:
                counts = data["per_label"].get(r["label"], {})
                counts[r["kind"]] = max(0, counts.get(r["kind"], 0) - 1)
                self._write(data)

    def summary(self) -> Dict[str, Any]:
        """For the admin endpoint: amounts and counts per access-code label. No prompts, codes or sessions."""
        with self._lock:
            try:
                data = self._load()
            except BudgetError as exc:
                return {"available": False, "reason": str(exc)}
            reserved = sum(r["micro"] for r in data["reserved"].values())
            return {
                "available": True,
                "total_usd": micro_to_usd(data["total_micro"]),
                "starting_spent_usd": micro_to_usd(data["starting_spent_micro"]),
                "spent_usd": micro_to_usd(data["spent_micro"]),
                "reserved_usd": micro_to_usd(reserved),
                "remaining_usd": micro_to_usd(max(0, data["total_micro"] - data["spent_micro"] - reserved)),
                "per_code": data["per_label"],
                "recent": [{k: e.get(k) for k in ("at", "kind", "label", "note")} | {"usd": micro_to_usd(e["micro"])}
                           for e in data["entries"][-20:]],
            }


ledger = Ledger()
