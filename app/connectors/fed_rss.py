from __future__ import annotations

import re
from datetime import datetime, timezone

import feedparser
import httpx

from .base import Connector, NewsItem

# Feed press release resmi The Fed. Cek ulang URL ini saat pertama dijalankan.
FED_PRESS_RSS = "https://www.federalreserve.gov/feeds/press_all.xml"


def _strip_html(text: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:400]


def _published_utc(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    # Missing publisher time stays unknown; ingestion time must not be used
    # as a fake publication time in historical entry context.
    return None


class FedRSSConnector(Connector):
    name = "fed_rss"
    interval_seconds = 30

    async def fetch(self, client: httpx.AsyncClient) -> list[NewsItem]:
        resp = await client.get(FED_PRESS_RSS, timeout=20)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)

        items: list[NewsItem] = []
        for e in feed.entries:
            link = e.get("link")
            published_at = _published_utc(e)
            if not link or not published_at:
                continue
            items.append(
                NewsItem(
                    external_id=f"fed:{e.get('id') or link}",
                    source="Federal Reserve",
                    title=(e.get("title") or "").strip(),
                    url=link,
                    summary=_strip_html(e.get("summary")),
                    published_at=published_at,
                    tier=1,
                    status="official",
                )
            )
        return items
