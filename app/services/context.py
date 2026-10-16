from __future__ import annotations

from datetime import datetime, timedelta

from ..config import settings
from ..db import get_db
from ..timeutil import fmt_utc

SNAPSHOT_LIMIT = 100


def build_context(entry_utc: datetime, known_at: datetime) -> list[dict]:
    """Berita dengan published_at di window [entry - N jam, entry] yang sudah masuk sistem pada known_at.

    known_at membatasi snapshot hanya pada apa yang benar-benar terlihat saat trade dicatat,
    jadi berita yang baru masuk belakangan tidak ikut.
    """
    start = entry_utc - timedelta(hours=settings.lookback_hours)
    with get_db() as db:
        rows = db.execute(
            """SELECT * FROM news
               WHERE published_at >= ? AND published_at <= ?
                 AND ingested_at <= ?
               ORDER BY published_at DESC
               LIMIT ?""",
            (fmt_utc(start), fmt_utc(entry_utc), fmt_utc(known_at), SNAPSHOT_LIMIT),
        ).fetchall()
    return [dict(r) for r in rows]
