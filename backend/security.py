"""Access control and usage limits for a shared deployment (the club demo).

Enabled with BUNYAN_AUTH=required (the Docker image sets it). Local development and
the test suite run with auth off, as before.

- Every request except GET /health needs HTTP Basic credentials from BUNYAN_USERS.
  The browser asks for them once; the frontend needs no change.
- Each project records its owner. Another user gets 404 for it, on every route
  (state, artifacts, preview, download).
- Failed logins are limited per client address.
- Per-user request rate, per-user daily projects and analyses, a global daily cap on
  real-LLM analyses, and a cap on analyses running at the same time. Daily counters
  are stored next to the projects, so a restart does not reset them.

BUNYAN_USERS holds "name:pbkdf2:<iterations>:<salt hex>:<hash hex>" entries separated
by commas or new lines (no "$", so compose files do not interpolate them). Create one with:

    python -m backend.security hash-password <name>
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, Optional, Tuple

from fastapi import HTTPException

PBKDF2_ITERATIONS = 200_000
REALM = "BUNYAN club demo"


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    if not raw.isdigit():
        raise RuntimeError(f"{name} must be a whole number, got '{raw}'")
    return int(raw)


def auth_required() -> bool:
    value = os.environ.get("BUNYAN_AUTH", "off").strip().lower()
    if value not in {"off", "required"}:
        raise RuntimeError(f"BUNYAN_AUTH must be 'off' or 'required', got '{value}'")
    return value == "required"


# ---------- passwords ----------

def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2:{iterations}:{salt.hex()}:{digest.hex()}"


def _check_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, expected = stored.split(":")
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations))
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), expected)


def load_users() -> Dict[str, str]:
    """Parse BUNYAN_USERS into {name: stored hash}. Raises RuntimeError on a malformed entry."""
    users: Dict[str, str] = {}
    raw = os.environ.get("BUNYAN_USERS", "")
    for entry in raw.replace("\n", ",").split(","):
        entry = entry.strip()
        if not entry:
            continue
        name, _, stored = entry.partition(":")
        if not name or not name.replace("-", "").replace("_", "").replace(".", "").isalnum() or not stored.startswith("pbkdf2:"):
            raise RuntimeError("BUNYAN_USERS has a malformed entry; create entries with "
                               "'python -m backend.security hash-password <name>'")
        users[name] = stored
    return users


def check_configuration() -> None:
    """Called at startup. With auth required, refuse to start without users."""
    if auth_required() and not load_users():
        raise RuntimeError("BUNYAN_AUTH=required but BUNYAN_USERS is empty: nobody could log in. "
                           "Add users with 'python -m backend.security hash-password <name>'.")
    for name in ("BUNYAN_MAX_PROJECTS_PER_USER_PER_DAY", "BUNYAN_MAX_ANALYSES_PER_USER_PER_DAY",
                 "BUNYAN_MAX_LLM_ANALYSES_PER_DAY", "BUNYAN_MAX_CONCURRENT_ANALYSES", "BUNYAN_MAX_REQUESTS_PER_MINUTE"):
        _int_env(name, 1)


class Authenticator:
    """Checks Basic credentials. A verified pair is cached briefly (PBKDF2 is slow on purpose)."""

    FAILURE_WINDOW = 300.0  # seconds
    MAX_FAILURES = 10       # per client address in the window

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: Dict[Tuple[str, str], float] = {}
        self._failures: Dict[str, Deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        with self._lock:
            self._cache.clear()
            self._failures.clear()

    def _blocked(self, client: str, now: float) -> bool:
        attempts = self._failures[client]
        while attempts and now - attempts[0] > self.FAILURE_WINDOW:
            attempts.popleft()
        return len(attempts) >= self.MAX_FAILURES

    def authenticate(self, header: Optional[str], client: str) -> str:
        """Return the user name or raise HTTPException (401, or 429 after too many failures)."""
        now = time.monotonic()
        with self._lock:
            if self._blocked(client, now):
                raise HTTPException(429, "محاولات دخول كثيرة. انتظر خمس دقائق ثم حاول مرة أخرى.")
        name, password = _parse_basic(header)
        if name is not None:
            key = (name, hashlib.sha256(password.encode("utf-8")).hexdigest())
            with self._lock:
                if self._cache.get(key, 0) > now:
                    return name
            stored = load_users().get(name)
            if stored and _check_password(password, stored):
                with self._lock:
                    self._cache[key] = now + 600
                return name
            with self._lock:
                self._failures[client].append(now)
        raise HTTPException(401, "سجّل الدخول باسم المستخدم وكلمة المرور.", headers={"WWW-Authenticate": f'Basic realm="{REALM}", charset="UTF-8"'})


def _parse_basic(header: Optional[str]) -> Tuple[Optional[str], str]:
    if not header or not header.lower().startswith("basic "):
        return None, ""
    try:
        decoded = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None, ""
    name, sep, password = decoded.partition(":")
    return (name, password) if sep and name else (None, "")


# ---------- ownership ----------

def can_access(project: dict, user: Optional[str]) -> bool:
    """With auth off everyone is the same local user. With auth on, only the owner."""
    if not auth_required():
        return True
    return user is not None and project.get("owner") == user


# ---------- limits ----------

class Limits:
    """Request rate, daily quotas and concurrency for analyses.

    Daily counters live in <data dir>/usage.json, keyed by UTC date, written atomically.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._running = 0

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
            self._running = 0

    # Rate of write requests (create, answers, approve) per user.
    def check_rate(self, user: str) -> None:
        limit = _int_env("BUNYAN_MAX_REQUESTS_PER_MINUTE", 20)
        now = time.monotonic()
        with self._lock:
            recent = self._requests[user]
            while recent and now - recent[0] > 60:
                recent.popleft()
            if len(recent) >= limit:
                raise HTTPException(429, "طلبات كثيرة في وقت قصير. انتظر دقيقة ثم أعد المحاولة.")
            recent.append(now)

    def _usage_path(self) -> Path:
        from backend import storage

        return Path(storage.DATA_DIR) / "usage.json"

    def _read(self) -> dict:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            data = json.loads(self._usage_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if data.get("date") != today:
            data = {"date": today, "projects": {}, "analyses": {}, "llm_analyses": 0}
        return data

    def _write(self, data: dict) -> None:
        path = self._usage_path()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)

    def reserve(self, user: str, new_project: bool, llm: bool) -> None:
        """Count one analysis (and one project) for the user, or raise 429. Call before any work."""
        max_projects = _int_env("BUNYAN_MAX_PROJECTS_PER_USER_PER_DAY", 10)
        max_analyses = _int_env("BUNYAN_MAX_ANALYSES_PER_USER_PER_DAY", 12)
        max_llm = _int_env("BUNYAN_MAX_LLM_ANALYSES_PER_DAY", 40)
        max_running = _int_env("BUNYAN_MAX_CONCURRENT_ANALYSES", 2)
        with self._lock:
            data = self._read()
            if new_project and data["projects"].get(user, 0) >= max_projects:
                raise HTTPException(429, f"وصلت إلى الحد اليومي للمشاريع ({max_projects}). جرّب غداً.")
            if data["analyses"].get(user, 0) >= max_analyses:
                raise HTTPException(429, f"وصلت إلى الحد اليومي للتحليل ({max_analyses}). جرّب غداً.")
            if llm and data["llm_analyses"] >= max_llm:
                raise HTTPException(429, "انتهت حصة التحليل بالذكاء الاصطناعي لهذا اليوم في العرض التجريبي. جرّب غداً.")
            if llm and self._running >= max_running:
                raise HTTPException(429, "المحلّل مشغول بطلبات أخرى الآن. أعد المحاولة بعد دقيقة.")
            if new_project:
                data["projects"][user] = data["projects"].get(user, 0) + 1
            data["analyses"][user] = data["analyses"].get(user, 0) + 1
            if llm:
                data["llm_analyses"] += 1
                self._running += 1
            self._write(data)

    def release(self) -> None:
        """An LLM analysis finished (or failed): free its concurrency slot."""
        with self._lock:
            self._running = max(0, self._running - 1)


authenticator = Authenticator()
limits = Limits()


def _main(argv) -> int:
    if len(argv) == 2 and argv[0] == "hash-password":
        import getpass

        password = getpass.getpass(f"Password for {argv[1]}: ")
        if len(password) < 10:
            print("Use at least 10 characters.", file=sys.stderr)
            return 1
        print(f"{argv[1]}:{hash_password(password)}")
        return 0
    print("usage: python -m backend.security hash-password <name>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
