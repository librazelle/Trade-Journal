from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from .base import Connector, NewsItem

# Official U.S. Bureau of Labor Statistics RSS feed.
BLS_LATEST_RSS = "https://www.bls.gov/feed/bls_latest.rss"


def _plain_text(value: str | None, limit: int = 400) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def _published_utc(entry) -> datetime | None:
    """Return the publisher timestamp when available; never fabricate one."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc)

    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return None
    return None


class BLSRSSConnector(Connector):
    """Official BLS release/news feed; not a substitute for the release calendar."""

    name = "bls_rss"
    interval_seconds = 60

    async def fetch(self, client: httpx.AsyncClient) -> list[NewsItem]:
        response = await client.get(BLS_LATEST_RSS, timeout=20)
        response.raise_for_status()
        feed = feedparser.parse(response.text)

        items: list[NewsItem] = []
        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            link = entry.get("link")
            published_at = _published_utc(entry)
            if not title or not link or published_at is None:
                # Missing timestamps are not replaced with ingestion time:
                # doing so would corrupt historical entry context.
                continue

            external_id = entry.get("id") or entry.get("guid") or link
            items.append(
                NewsItem(
                    external_id=f"bls:{external_id}",
                    source="U.S. Bureau of Labor Statistics",
                    title=title,
                    url=link,
                    summary=_plain_text(entry.get("summary") or entry.get("description")),
                    published_at=published_at,
                    tier=1,
                    status="official",
                )
            )
        return items
