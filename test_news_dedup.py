from datetime import datetime, timezone

from app.config import settings
from app.db import init_db, get_db
from app.connectors.base import NewsItem
from app.services.news import save_items


def test_duplicate_rss_item_is_not_saved_twice(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "news.db"))
    init_db()
    item = NewsItem(
        external_id="test-source:unique-123",
        source="Test Source",
        title="US CPI test release headline",
        published_at=datetime.now(timezone.utc),
        url="https://example.com/test-release",
        summary="Inflation test summary",
        tier=1,
        status="official",
    )

    first = save_items([item])
    second = save_items([item])

    assert len(first) == 1
    assert len(second) == 0
    with get_db() as db:
        count = db.execute(
            "SELECT COUNT(*) FROM news WHERE external_id = ?",
            ("test-source:unique-123",),
        ).fetchone()[0]
    assert count == 1
