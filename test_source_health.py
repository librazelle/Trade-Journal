from datetime import datetime, timedelta, timezone

from app.services.source_health import record_poll, snapshot
from app.timeutil import fmt_utc


def _source(name):
    return next(item for item in snapshot() if item["name"] == name)


def test_successful_poll_is_live():
    name = "test_live_connector"
    record_poll(name, True, item_count=3)
    result = _source(name)
    assert result["status"] == "LIVE"
    assert result["last_success_at"] is not None
    assert result["last_error"] is None


def test_recent_news_with_high_ingestion_latency_is_delayed():
    name = "test_delayed_connector"
    now = datetime.now(timezone.utc)
    row = {
        "published_at": fmt_utc(now - timedelta(minutes=12)),
        "ingested_at": fmt_utc(now),
    }
    record_poll(name, True, item_count=1, new_rows=[row])
    result = _source(name)
    assert result["status"] == "DELAYED"
    assert result["last_new_item_delay_min"] >= 11
