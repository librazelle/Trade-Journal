"""Fetch and normalize scheduled releases from the official BLS calendar.

The BLS page is authoritative for BLS release dates. This module deliberately
leaves forecast, previous and actual empty: those values must come from a
separate licensed/official source and must never be guessed.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import httpx

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
DATE_RE = re.compile(rf"\b(?:{MONTHS})\s+\d{{1,2}},\s+\d{{4}}\b", re.I)
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", re.I)


class _ScheduleParser(HTMLParser):
    """Small stdlib-only table parser; avoids adding a scraping dependency."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict]] = []
        self.row = None
        self.cell = None
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = {"text": [], "links": []}
            self.row.append(self.cell)
        elif tag == "a" and self.cell is not None:
            self.anchor = {"href": attrs.get("href"), "text": []}

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"].append(data)
        if self.anchor is not None:
            self.anchor["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            label = " ".join(" ".join(self.anchor["text"]).split())
            href = self.anchor.get("href")
            if label and href and self.cell is not None:
                self.cell["links"].append((label, href))
            self.anchor = None
        elif tag in ("td", "th"):
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None


def _impact(title: str) -> str:
    title_upper = title.upper()
    if any(term in title_upper for term in (
        "CONSUMER PRICE INDEX", "CPI", "PRODUCER PRICE INDEX", "PPI",
        "EMPLOYMENT SITUATION", "PRODUCTIVITY AND COSTS",
    )):
        return "high"
    if any(term in title_upper for term in (
        "JOB OPENINGS", "JOLTS", "EMPLOYMENT COST", "REAL EARNINGS",
        "IMPORT AND EXPORT PRICE", "UNEMPLOYMENT",
    )):
        return "medium"
    return "low"


def _absolute_url(href: str) -> str:
    if href.startswith("https://") or href.startswith("http://"):
        return href
    if href.startswith("/"):
        return "https://www.bls.gov" + href
    return "https://www.bls.gov/" + href.lstrip("./")


def parse_bls_schedule(html: str, year: int) -> list[dict]:
    """Parse the BLS annual release schedule into UTC event records."""
    parser = _ScheduleParser()
    parser.feed(html)
    events: dict[str, dict] = {}

    for row in parser.rows:
        cells = [
            {
                "text": " ".join(" ".join(cell["text"]).split()),
                "links": cell["links"],
            }
            for cell in row
        ]
        row_text = " | ".join(cell["text"] for cell in cells)
        date_match = DATE_RE.search(row_text)
        time_match = TIME_RE.search(row_text)
        if not date_match or not time_match:
            continue

        try:
            day = datetime.strptime(date_match.group(0), "%B %d, %Y").date()
            clock = datetime.strptime(time_match.group(0).upper().replace(" ", ""), "%I:%M%p").time()
        except ValueError:
            continue
        if day.year != year:
            continue

        title = ""
        source_url = f"https://www.bls.gov/schedule/{year}/home.htm"
        for cell in cells:
            for label, href in cell["links"]:
                if label.strip() and not DATE_RE.fullmatch(label.strip()) and not TIME_RE.fullmatch(label.strip()):
                    title, source_url = label.strip(), _absolute_url(href)
                    break
            if title:
                break
        if not title:
            candidates = [
                cell["text"] for cell in cells
                if cell["text"] and not DATE_RE.fullmatch(cell["text"])
                and not TIME_RE.fullmatch(cell["text"])
            ]
            if not candidates:
                continue
            title = max(candidates, key=len)

        local_dt = datetime.combine(day, clock, tzinfo=ET)
        scheduled_utc = local_dt.astimezone(UTC).isoformat().replace("+00:00", "Z")
        key = hashlib.sha256(f"{title.lower()}|{scheduled_utc}".encode()).hexdigest()[:24]
        events[key] = {
            "event_id": f"bls:{key}",
            "name": title,
            "country": "US",
            "scheduled_at_utc": scheduled_utc,
            "impact": _impact(title),
            "source": "U.S. Bureau of Labor Statistics",
            "url": source_url,
            "forecast": None,
            "previous": None,
            "actual": None,
        }

    return sorted(events.values(), key=lambda event: event["scheduled_at_utc"])


async def fetch_bls_calendar(client: httpx.AsyncClient, year: int) -> list[dict]:
    """Fetch the official annual BLS schedule; errors are surfaced to the caller."""
    url = f"https://www.bls.gov/schedule/{year}/home.htm"
    response = await client.get(url, timeout=20)
    response.raise_for_status()
    events = parse_bls_schedule(response.text, year)
    if not events:
        raise ValueError(f"No BLS schedule events parsed from {url}; parser may need updating")
    return events
