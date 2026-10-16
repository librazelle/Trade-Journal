from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db import get_db, init_db
from app.services.calendar_store import ensure_calendar_table
from app.services.economic_context import build_economic_context
from app.timeutil import fmt_utc


UTC = timezone.utc


def _insert_event(name, scheduled_at, fetched_at):
    with get_db() as db:
        db.execute(
            """INSERT INTO econ_events
               (event_id, name, country, scheduled_at_utc, impact, source, url,
                forecast, previous, actual, fetched_at)
               VALUES (?, ?, 'US', ?, 'high', 'U.S. Bureau of Labor Statistics',
                       'https://www.bls.gov/', NULL, NULL, NULL, ?)""",
            (f"test:{name.lower().replace(' ', '-')}", name, fmt_utc(scheduled_at), fmt_utc(fetched_at)),
        )


def test_economic_context_is_frozen_to_known_calendar_data(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "economic-context.db"))
    init_db()
    ensure_calendar_table()

    entry = datetime(2026, 10, 16, 14, 0, tzinfo=UTC)
    known_at = entry + timedelta(minutes=1)
    _insert_event("CPI before entry", entry - timedelta(hours=2), entry - timedelta(minutes=10))
    _insert_event("NFP after entry", entry + timedelta(hours=3), entry - timedelta(minutes=10))
    _insert_event("Fetched after entry", entry + timedelta(hours=1), entry + timedelta(minutes=2))
    _insert_event("Outside forward window", entry + timedelta(hours=30), entry - timedelta(minutes=10))

    events = build_economic_context(entry, known_at)
    assert [event["name"] for event in events] == ["CPI before entry", "NFP after entry"]
    assert events[0]["relation_to_entry"] == "before"
    assert events[1]["relation_to_entry"] == "after"


def test_economic_context_empty_when_no_schedule_was_known(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "empty-economic-context.db"))
    init_db()
    ensure_calendar_table()

    entry = datetime(2026, 10, 16, 14, 0, tzinfo=UTC)
    _insert_event("Unknown at entry", entry + timedelta(hours=1), entry + timedelta(minutes=5))

    assert build_economic_context(entry, entry + timedelta(minutes=1)) == []
