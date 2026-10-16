"""Additive SQLite storage for normalized economic calendar events."""
from __future__ import annotations

from datetime import datetime, timezone

from ..db import get_db
from ..timeutil import fmt_utc


def ensure_calendar_table() -> None:
    """Create the calendar table without modifying existing trade/news tables."""
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS econ_events (
                event_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                country TEXT NOT NULL DEFAULT 'US',
                scheduled_at_utc TEXT NOT NULL,
                impact TEXT NOT NULL DEFAULT 'medium'
                    CHECK (impact IN ('high', 'medium', 'low')),
                source TEXT NOT NULL,
                url TEXT,
                forecast TEXT,
                previous TEXT,
                actual TEXT,
                fetched_at TEXT NOT NULL
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_econ_events_scheduled "
            "ON econ_events(scheduled_at_utc)"
        )


def save_calendar_events(events: list[dict]) -> None:
    fetched_at = fmt_utc(datetime.now(timezone.utc))
    with get_db() as db:
        for event in events:
            db.execute("""
                INSERT INTO econ_events
                    (event_id, name, country, scheduled_at_utc, impact, source,
                     url, forecast, previous, actual, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    name=excluded.name,
                    country=excluded.country,
                    scheduled_at_utc=excluded.scheduled_at_utc,
                    impact=excluded.impact,
                    source=excluded.source,
                    url=excluded.url,
                    fetched_at=excluded.fetched_at
            """, (
                event["event_id"], event["name"], event.get("country", "US"),
                event["scheduled_at_utc"], event.get("impact", "medium"),
                event["source"], event.get("url"), event.get("forecast"),
                event.get("previous"), event.get("actual"), fetched_at,
            ))


def list_calendar_events(year: int) -> list[dict]:
    ensure_calendar_table()
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM econ_events WHERE substr(scheduled_at_utc, 1, 4) = ? "
            "ORDER BY scheduled_at_utc ASC",
            (str(year),),
        ).fetchall()
    return [dict(row) for row in rows]
