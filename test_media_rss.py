from datetime import datetime, timezone
from email.utils import format_datetime

import asyncio

import httpx

from app.connectors.media_rss import (
    BBCBusinessRSSConnector,
    BBCWorldRSSConnector,
    GuardianBusinessRSSConnector,
    GuardianWorldRSSConnector,
    _plain_text,
    _published_utc,
)


def test_editorial_connectors_cover_world_and_business():
    connectors = [
        BBCWorldRSSConnector(),
        BBCBusinessRSSConnector(),
        GuardianWorldRSSConnector(),
        GuardianBusinessRSSConnector(),
    ]
    assert len({connector.name for connector in connectors}) == 4
    assert all(connector.feed_url.startswith("https://") for connector in connectors)
    assert all(connector.interval_seconds == 90 for connector in connectors)


def test_plain_text_strips_markup_and_collapses_whitespace():
    assert _plain_text("<p>World <b>markets</b></p>\n news") == "World markets news"


def test_published_time_is_utc_and_missing_time_is_not_fabricated():
    entry = {"published_parsed": (2026, 10, 17, 1, 2, 3, 5, 290, 0)}
    assert _published_utc(entry) == datetime(2026, 10, 17, 1, 2, 3, tzinfo=timezone.utc)
    assert _published_utc({}) is None


def test_fetch_parses_feed_and_marks_media_as_reported():
    published = format_datetime(datetime(2026, 10, 17, 1, 2, tzinfo=timezone.utc))
    xml = f"""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>BBC World</title>
      <item><title>Tariff dispute escalates</title>
        <link>https://example.test/story/1</link>
        <guid>story-1</guid><pubDate>{published}</pubDate>
        <description><![CDATA[Leaders discuss trade policy.]]></description>
      </item></channel></rss>"""

    async def handler(request):
        return httpx.Response(200, text=xml, request=request)

    async def run_fetch():
        connector = BBCWorldRSSConnector()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await connector.fetch(client)

    items = asyncio.run(run_fetch())

    assert len(items) == 1
    assert items[0].external_id == "bbc-world:story-1"
    assert items[0].source == "BBC News · World"
    assert items[0].tier == 2
    assert items[0].status == "reported"
    assert items[0].published_at == datetime(2026, 10, 17, 1, 2, tzinfo=timezone.utc)
