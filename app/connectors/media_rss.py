"""Additional editorial RSS sources for world affairs and global business news.""" 
from __future__ import annotations

import re
from datetime import datetime, timezone

import feedparser
import httpx

from .base import Connector, NewsItem


def _plain_text(value: str | None, limit: int = 500) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _published_utc(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return None
    return None


class EditorialRSSConnector(Connector):
    """A single editorial RSS feed. Each feed has its own health status and dedup namespace."""

    interval_seconds = 90
    feed_url = ""
    source_name = ""
    source_key = ""

    async def fetch(self, client: httpx.AsyncClient) -> list[NewsItem]:
        response = await client.get(self.feed_url, timeout=20)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        items: list[NewsItem] = []
        for entry in feed.entries:
            title = _plain_text(entry.get("title"), 300)
            link = entry.get("link")
            published_at = _published_utc(entry)
            if not title or not link or not published_at:
                continue
            external_id = entry.get("id") or entry.get("guid") or link
            items.append(
                NewsItem(
                    external_id=f"{self.source_key}:{external_id}",
                    source=self.source_name,
                    title=title,
                    url=link,
                    summary=_plain_text(entry.get("summary") or entry.get("description")),
                    published_at=published_at,
                    tier=2,
                    status="reported",
                )
            )
        return items


class BBCWorldRSSConnector(EditorialRSSConnector):
    name = "bbc_world_rss"
    feed_url = "https://feeds.bbci.co.uk/news/world/rss.xml"
    source_name = "BBC News · World"
    source_key = "bbc-world"


class BBCBusinessRSSConnector(EditorialRSSConnector):
    name = "bbc_business_rss"
    feed_url = "https://feeds.bbci.co.uk/news/business/rss.xml"
    source_name = "BBC News · Business"
    source_key = "bbc-business"


class BBCEconomicsRSSConnector(EditorialRSSConnector):
    name = "bbc_economics_rss"
    feed_url = "https://feeds.bbci.co.uk/news/business/economy/rss.xml"
    source_name = "BBC News · Economics"
    source_key = "bbc-economics"


class GuardianWorldRSSConnector(EditorialRSSConnector):
    name = "guardian_world_rss"
    feed_url = "https://www.theguardian.com/world/rss"
    source_name = "The Guardian · World"
    source_key = "guardian-world"


class GuardianBusinessRSSConnector(EditorialRSSConnector):
    name = "guardian_business_rss"
    feed_url = "https://www.theguardian.com/business/rss"
    source_name = "The Guardian · Business"
    source_key = "guardian-business"
