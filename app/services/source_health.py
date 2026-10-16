"""In-memory health state for RSS polling connectors."""
from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

from ..timeutil import fmt_utc, parse_utc

_lock = Lock()
_state: dict[str, dict] = {}


def record_poll(name: str, success: bool, item_count: int = 0,
                new_rows: list[dict] | None = None, error: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    with _lock:
        state = _state.setdefault(name, {
            "name": name, "last_attempt_at": None, "last_success_at": None,
            "last_error": None, "last_item_count": 0,
            "last_new_item_at": None, "last_new_item_delay_min": None,
        })
        state["last_attempt_at"] = fmt_utc(now)
        state["last_item_count"] = item_count
        state["last_error"] = (error[:240] if error else None)
        if success:
            state["last_success_at"] = state["last_attempt_at"]
            state["last_error"] = None
        for row in new_rows or []:
            try:
                published = parse_utc(row["published_at"])
                ingested = parse_utc(row["ingested_at"])
                delay = max(0.0, (ingested - published).total_seconds() / 60)
            except (KeyError, TypeError, ValueError):
                continue
            if state["last_new_item_at"] is None or row["ingested_at"] >= state["last_new_item_at"]:
                state["last_new_item_at"] = row["ingested_at"]
                state["last_new_item_delay_min"] = round(delay, 1)


def snapshot() -> list[dict]:
    now = datetime.now(timezone.utc)
    with _lock:
        states = [dict(value) for value in _state.values()]
    for state in states:
        last_success = state["last_success_at"]
        if not last_success:
            status = "OFFLINE" if state["last_attempt_at"] and state["last_error"] else "STALE"
        else:
            age = (now - parse_utc(last_success)).total_seconds()
            if age > 90:
                status = "STALE"
            else:
                item_time = state["last_new_item_at"]
                recent_item = False
                if item_time:
                    try:
                        recent_item = (now - parse_utc(item_time)).total_seconds() <= 86400
                    except ValueError:
                        recent_item = False
                delay = state["last_new_item_delay_min"]
                status = "DELAYED" if recent_item and delay is not None and delay > 5 else "LIVE"
        state["status"] = status
        state["last_success_age_seconds"] = (
            round((now - parse_utc(last_success)).total_seconds())
            if last_success else None
        )
    return sorted(states, key=lambda item: item["name"])
