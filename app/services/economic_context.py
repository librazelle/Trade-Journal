"""Freeze economic-calendar context that was already known at trade entry."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..db import get_db
from ..timeutil import fmt_utc
from .calendar_store import ensure_calendar_table


def build_economic_context(
    entry_utc: datetime,
    known_at: datetime,
    lookback_hours: int = 5,
    forward_hours: int = 24,
) -> list[dict]:
    """Snapshot scheduled events around entry, excluding calendar data fetched later.

    Events are selected from entry-lookback through entry+forward, but only if the
    schedule had already been fetched by known_at. This prevents later calendar
    refreshes from silently changing the historical entry context.
    """
    ensure_calendar_table()
    start = fmt_utc(entry_utc - timedelta(hours=lookback_hours))
    end = fmt_utc(entry_utc + timedelta(hours=forward_hours))
    cutoff = fmt_utc(known_at)

    with get_db() as db:
        rows = db.execute(
            """SELECT event_id, name, country, scheduled_at_utc, impact, source, url
               FROM econ_events
               WHERE scheduled_at_utc >= ? AND scheduled_at_utc <= ?
                 AND fetched_at <= ?
               ORDER BY scheduled_at_utc ASC""",
            (start, end, cutoff),
        ).fetchall()

    result = []
    for row in rows:
        event = dict(row)
        scheduled = datetime.strptime(
            event["scheduled_at_utc"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=entry_utc.tzinfo)
        delta_hours = (scheduled - entry_utc).total_seconds() / 3600
        event["relation_to_entry"] = (
            "before" if delta_hours < 0 else "after" if delta_hours > 0 else "at_entry"
        )
        event["hours_from_entry"] = round(delta_hours, 2)
        result.append(event)
    return result
