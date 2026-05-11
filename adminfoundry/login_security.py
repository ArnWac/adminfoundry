"""Per-email account lockout after repeated login failures."""
import time
from adminfoundry.settings import settings

# email → list of failure timestamps
_failures: dict[str, list[float]] = {}


def _window() -> int:
    return settings.LOGIN_LOCKOUT_MINUTES * 60


def _trim(email: str, now: float) -> list[float]:
    hits = [t for t in _failures.get(email, []) if t > now - _window()]
    _failures[email] = hits
    return hits


def is_locked(email: str) -> bool:
    hits = _trim(email, time.time())
    return len(hits) >= settings.LOGIN_MAX_FAILURES


def record_failure(email: str) -> None:
    now = time.time()
    hits = _trim(email, now)
    hits.append(now)
    _failures[email] = hits


def clear_failures(email: str) -> None:
    _failures.pop(email, None)


def reset_lockouts() -> None:
    """Test helper — clear all lockout state."""
    _failures.clear()
