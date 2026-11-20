"""Access control and usage limits for a shared deployment (the club demo).

BUNYAN_AUTH chooses how a visitor gets an identity:
- required: HTTP Basic credentials from BUNYAN_USERS on every request except GET /health.
  The browser asks for them once; the frontend needs no change. (The Docker default.)
- guest: no login. The server issues each new visitor an anonymous guest identity in a
  signed, HttpOnly, Secure, SameSite=Lax cookie (HMAC-SHA256 with BUNYAN_SESSION_SECRET,
  valid 7 days). Every guest is a separate owner. Guest mode never calls a paid model.
- off: local development and the test suite; everyone is the same local user.

In required and guest mode:
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


def auth_mode() -> str:
    value = os.environ.get("BUNYAN_AUTH", "off").strip().lower()
    if value not in {"off", "required", "guest"}:
        raise RuntimeError(f"BUNYAN_AUTH must be 'off', 'required' or 'guest', got '{value}'")
    return value


def auth_required() -> bool:
    return auth_mode() == "required"


def shared_deployment() -> bool:
    """Several people use this server: ownership checks and limits apply."""
    return auth_mode() in {"required", "guest"}


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
    """Called at startup: refuse to run a shared deployment that is not configured safely."""
    mode = auth_mode()
    if mode == "required" and not load_users():
        raise RuntimeError("BUNYAN_AUTH=required but BUNYAN_USERS is empty: nobody could log in. "
                           "Add users with 'python -m backend.security hash-password <name>'.")
    if mode == "guest":
        _session_secret()  # raises when missing or too short
        if os.environ.get("BA_MODE", "mock").strip().lower() != "mock":
            raise RuntimeError("BUNYAN_AUTH=guest only runs with BA_MODE=mock: anonymous guests must never "
                               "cause paid model requests. Use BUNYAN_AUTH=required for the real analyst.")
    for name in ("BUNYAN_MAX_PROJECTS_PER_USER_PER_DAY", "BUNYAN_MAX_ANALYSES_PER_USER_PER_DAY",
                 "BUNYAN_MAX_LLM_ANALYSES_PER_DAY", "BUNYAN_MAX_CONCURRENT_ANALYSES", "BUNYAN_MAX_REQUESTS_PER_MINUTE",
                 "BUNYAN_MAX_REQUESTS_PER_MINUTE_PER_IP", "BUNYAN_MAX_PROJECTS_PER_IP_PER_DAY",
                 "BUNYAN_MAX_PROJECTS_PER_DAY", "BUNYAN_MAX_NEW_SESSIONS_PER_IP_PER_HOUR"):
        _int_env(name, 1)


# ---------- guest sessions ----------

GUEST_COOKIE = "bunyan_guest"
GUEST_SESSION_SECONDS = 7 * 24 * 3600


def _session_secret() -> bytes:
    secret = os.environ.get("BUNYAN_SESSION_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("BUNYAN_AUTH=guest needs BUNYAN_SESSION_SECRET of at least 32 characters "
                           "(for example: python -c \"import secrets; print(secrets.token_urlsafe(48))\").")
    return secret.encode("utf-8")


def _session_mac(payload: str) -> str:
    return hmac.new(_session_secret(), payload.encode("ascii"), hashlib.sha256).hexdigest()


def issue_guest_cookie(now: Optional[float] = None) -> Tuple[str, str]:
    """A new guest: (user name, cookie value). The id is 24 random bytes from secrets."""
    sid = secrets.token_urlsafe(24)
    payload = f"{sid}.{int(now if now is not None else time.time())}"
    return f"guest:{sid}", f"{payload}.{_session_mac(payload)}"


def read_guest_cookie(value: Optional[str], now: Optional[float] = None) -> Optional[str]:
    """The guest user name for a valid, unexpired, untampered cookie; otherwise None."""
    if not value or len(value) > 200:
        return None
    parts = value.split(".")
    if len(parts) != 3 or not parts[1].isdigit():
        return None
    sid, issued, mac = parts
    if not sid or not all(c.isalnum() or c in "-_" for c in sid):
        return None
    if not hmac.compare_digest(_session_mac(f"{sid}.{issued}"), mac):
        return None
    age = (now if now is not None else time.time()) - int(issued)
    if age < 0 or age > GUEST_SESSION_SECONDS:
        return None
    return f"guest:{sid}"


class GuestSessions:
    """Limits how many new guest identities one address can get (quota bypass by clearing cookies)."""

    WINDOW = 3600.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._issued: Dict[str, Deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        with self._lock:
            self._issued.clear()

    def identify(self, cookie: Optional[str], client: str) -> Tuple[str, Optional[str]]:
        """(user, new cookie value or None). Raises 429 when the address made too many guests."""
        user = read_guest_cookie(cookie)
        if user is not None:
            return user, None
        limit = _int_env("BUNYAN_MAX_NEW_SESSIONS_PER_IP_PER_HOUR", 30)
        now = time.monotonic()
        with self._lock:
            issued = self._issued[client]
            while issued and now - issued[0] > self.WINDOW:
                issued.popleft()
            if len(issued) >= limit:
                raise HTTPException(429, "جلسات جديدة كثيرة من هذا الجهاز أو الشبكة. انتظر قليلاً ثم أعد المحاولة.")
            issued.append(now)
        return issue_guest_cookie()


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
    """With auth off everyone is the same local user. Otherwise only the owner (each guest is one owner)."""
    if not shared_deployment():
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

    # Rate of write requests (create, answers, approve) per user and per address.
    def check_rate(self, user: str, client: str = "unknown") -> None:
        limits = [(f"user:{user}", _int_env("BUNYAN_MAX_REQUESTS_PER_MINUTE", 20)),
                  (f"ip:{client}", _int_env("BUNYAN_MAX_REQUESTS_PER_MINUTE_PER_IP", 60))]
        now = time.monotonic()
        with self._lock:
            for key, limit in limits:
                recent = self._requests[key]
                while recent and now - recent[0] > 60:
                    recent.popleft()
                if len(recent) >= limit:
                    raise HTTPException(429, "طلبات كثيرة في وقت قصير. انتظر دقيقة ثم أعد المحاولة.")
            for key, _ in limits:
                self._requests[key].append(now)

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
        data.setdefault("projects_by_ip", {})
        data.setdefault("projects_total", sum(data["projects"].values()))
        return data

    def _write(self, data: dict) -> None:
        path = self._usage_path()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)

    def reserve(self, user: str, new_project: bool, llm: bool, client: str = "unknown") -> None:
        """Count one analysis (and one project) for the user, or raise 429. Call before any work.

        A new project also counts for the client address and for the whole site, so new
        guest cookies cannot buy unlimited projects.
        """
        max_projects = _int_env("BUNYAN_MAX_PROJECTS_PER_USER_PER_DAY", 10)
        max_per_ip = _int_env("BUNYAN_MAX_PROJECTS_PER_IP_PER_DAY", 40)
        max_total = _int_env("BUNYAN_MAX_PROJECTS_PER_DAY", 300)
        max_analyses = _int_env("BUNYAN_MAX_ANALYSES_PER_USER_PER_DAY", 12)
        max_llm = _int_env("BUNYAN_MAX_LLM_ANALYSES_PER_DAY", 40)
        max_running = _int_env("BUNYAN_MAX_CONCURRENT_ANALYSES", 2)
        with self._lock:
            data = self._read()
            if new_project and data["projects"].get(user, 0) >= max_projects:
                raise HTTPException(429, f"وصلت إلى الحد اليومي للمشاريع ({max_projects}). جرّب غداً.")
            if new_project and data["projects_by_ip"].get(client, 0) >= max_per_ip:
                raise HTTPException(429, "وصلت هذه الشبكة إلى الحد اليومي للمشاريع في العرض التجريبي. جرّب غداً.")
            if new_project and data["projects_total"] >= max_total:
                raise HTTPException(429, "اكتمل عدد المشاريع المتاح اليوم في العرض التجريبي. جرّب غداً.")
            if data["analyses"].get(user, 0) >= max_analyses:
                raise HTTPException(429, f"وصلت إلى الحد اليومي للتحليل ({max_analyses}). جرّب غداً.")
            if llm and data["llm_analyses"] >= max_llm:
                raise HTTPException(429, "انتهت حصة التحليل بالذكاء الاصطناعي لهذا اليوم في العرض التجريبي. جرّب غداً.")
            if llm and self._running >= max_running:
                raise HTTPException(429, "المحلّل مشغول بطلبات أخرى الآن. أعد المحاولة بعد دقيقة.")
            if new_project:
                data["projects"][user] = data["projects"].get(user, 0) + 1
                data["projects_by_ip"][client] = data["projects_by_ip"].get(client, 0) + 1
                data["projects_total"] += 1
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
guest_sessions = GuestSessions()
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
