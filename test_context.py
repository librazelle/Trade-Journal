from datetime import datetime, timedelta, timezone

from app.config import settings
from app.connectors.base import NewsItem
from app.db import init_db
from app.services.context import build_context
from app.services.news import save_items

UTC = timezone.utc


def _item(ext, title, published):
    return NewsItem(external_id=ext, source="Test", title=title,
                    published_at=published, tier=1, status="official")


def test_context_window_and_known_at(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "ctx.db"))
    monkeypatch.setattr(settings, "lookback_hours", 5)
    init_db()

    entry = datetime(2026, 10, 16, 8, 0, tzinfo=UTC)
    known_at = entry + timedelta(minutes=30)

    # Terbit dan masuk sistem sebelum entry: masuk window
    save_items([
        _item("a", "dalam window", entry - timedelta(hours=2)),
        _item("b", "terlalu lama", entry - timedelta(hours=6)),
    ], ingested_at=entry - timedelta(hours=1))

    # Terbit sebelum entry tapi baru masuk setelah known_at: dikecualikan
    save_items([_item("c", "masuk belakangan", entry - timedelta(hours=1))],
               ingested_at=known_at + timedelta(minutes=5))

    # Terbit setelah entry: di luar window
    save_items([_item("d", "setelah entry", entry + timedelta(hours=1))],
               ingested_at=entry + timedelta(hours=1, minutes=1))

    titles = [r["title"] for r in build_context(entry, known_at)]
    assert titles == ["dalam window"]


def test_dedup(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "dedup.db"))
    init_db()

    now = datetime(2026, 10, 16, 8, 0, tzinfo=UTC)
    first = save_items([_item("x", "sama", now)])
    second = save_items([_item("x", "sama", now)])
    assert len(first) == 1
    assert second == []
