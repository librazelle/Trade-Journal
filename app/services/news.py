from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from ..connectors.base import NewsItem
from ..db import get_db
from ..timeutil import fmt_utc, parse_utc
from .tagging import impact_score, tag_text
from .news_explain import explain_news


def save_items(items: Iterable[NewsItem], ingested_at: datetime | None = None) -> list[dict]:
    """Simpan item baru dan lewati yang sudah ada. Mengembalikan hanya row yang benar-benar baru."""
    ingested_at = ingested_at or datetime.now(timezone.utc)
    new_rows: list[dict] = []
    with get_db() as db:
        for it in items:
            tags = tag_text(f"{it.title} {it.summary or ''}")
            cur = db.execute(
                """INSERT OR IGNORE INTO news
                   (external_id, source, tier, status, title, url, summary,
                    tags, impact, published_at, ingested_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    it.external_id, it.source, it.tier, it.status, it.title,
                    it.url, it.summary, ",".join(tags), impact_score(it.tier, tags),
                    fmt_utc(it.published_at), fmt_utc(ingested_at),
                ),
            )
            if cur.rowcount == 1:
                row = db.execute("SELECT * FROM news WHERE id = ?", (cur.lastrowid,)).fetchone()
                new_rows.append(dict(row))
    return new_rows


def news_view(row) -> dict:
    """Ubah row atau dict berita menjadi bentuk siap-render: tags list, delay, dan url yang aman."""
    d = dict(row)
    d["tags_list"] = [t for t in (d.get("tags") or "").split(",") if t]
    d.update(explain_news(d.get("title", ""), d.get("summary", ""), d.get("tags", "")))
    url = d.get("url") or ""
    d["url"] = url if url.startswith(("http://", "https://")) else None
    try:
        delta = parse_utc(d["ingested_at"]) - parse_utc(d["published_at"])
        d["delay_min"] = round(delta.total_seconds() / 60, 1)
    except (KeyError, TypeError, ValueError):
        d["delay_min"] = None
    return d
