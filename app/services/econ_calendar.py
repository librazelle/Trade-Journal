"""Normalize the official BLS annual release schedule into UTC event records."""
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
DATE_RE = re.compile(rf"\b(?:{MONTHS})\s+\d{1,2},\s+\d{4}\b", re.I)
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", re.I)
BLOCK_TAGS = {"br", "p", "li", "tr", "h1", "h2", "h3", "div", "section"}


class _ScheduleParser(HTMLParser):
    """Capture table cells and visible lines without a third-party HTML parser."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict]] = []
        self.row = None
        self.cell = None
        self.anchor = None
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in BLOCK_TAGS:
            self.text_parts.append("\n")
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = {"text": [], "links": []}
            self.row.append(self.cell)
        elif tag == "a":
            self.anchor = {"href": attrs.get("href"), "text": []}

    def handle_data(self, data):
        self.text_parts.append(data)
        if self.cell is not None:
            self.cell["text"].append(data)
        if self.anchor is not None:
            self.anchor["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor is not None:
            label = " ".join(" ".join(self.anchor["text"]).split())
            href = self.anchor.get("href")
            if label and href:
                self.links.append((label, href))
                if self.cell is not None:
                    self.cell["links"].append((label, href))
            self.anchor = None
        elif tag in ("td", "th"):
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
        if tag in BLOCK_TAGS:
            self.text_parts.append("\n")


def _impact(title: str) -> str:
    value = title.upper()
    if any(term in value for term in (
        "CONSUMER PRICE INDEX", "CPI", "PRODUCER PRICE INDEX", "PPI",
        "EMPLOYMENT SITUATION", "PRODUCTIVITY AND COSTS",
    )):
        return "high"
    if any(term in value for term in (
        "JOB OPENINGS", "JOLTS", "EMPLOYMENT COST", "REAL EARNINGS",
        "IMPORT AND EXPORT PRICE", "UNEMPLOYMENT",
    )):
        return "medium"
    return "low"


def _absolute_url(href: str) -> str:
    if href.startswith(("https://", "http://")):
        return href
    if href.startswith("/"):
        return "https://www.bls.gov" + href
    return "https://www.bls.gov/" + href.lstrip("./")


def _event(title: str, date_text: str, time_text: str, year: int, url: str) -> dict | None:
    try:
        day = datetime.strptime(date_text, "%B %d, %Y").date()
        clock = datetime.strptime(time_text.upper().replace(" ", ""), "%I:%M%p").time()
    except ValueError:
        return None
    if day.year != year:
        return None
    scheduled_utc = datetime.combine(day, clock, tzinfo=ET).astimezone(UTC).isoformat().replace("+00:00", "Z")
    key = hashlib.sha256(f"{title.lower()}|{scheduled_utc}".encode()).hexdigest()[:24]
    return {
        "event_id": f"bls:{key}",
        "name": title,
        "country": "US",
        "scheduled_at_utc": scheduled_utc,
        "impact": _impact(title),
        "source": "U.S. Bureau of Labor Statistics",
        "url": url,
        "forecast": None,
        "previous": None,
        "actual": None,
    }


def parse_bls_schedule(html: str, year: int) -> list[dict]:
    """Parse BLS schedule tables or list-view rows; timestamps are published in ET."""
    parser = _ScheduleParser()
    parser.feed(html)
    events: dict[str, dict] = {}

    # Table-style markup, if the publisher changes the page layout back to tables.
    for row in parser.rows:
        cells = [
            {"text": " ".join(" ".join(cell["text"]).split()), "links": cell["links"]}
            for cell in row
        ]
        row_text = " | ".join(cell["text"] for cell in cells)
        date_match = DATE_RE.search(row_text)
        time_match = TIME_RE.search(row_text)
        if not date_match or not time_match:
            continue
        title = ""
        url = f"https://www.bls.gov/schedule/{year}/home.htm"
        for cell in cells:
            for label, href in cell["links"]:
                if label.strip() and not DATE_RE.fullmatch(label.strip()) and not TIME_RE.fullmatch(label.strip()):
                    title, url = label.strip(), _absolute_url(href)
                    break
            if title:
                break
        if not title:
            candidates = [
                cell["text"] for cell in cells
                if cell["text"] and not DATE_RE.fullmatch(cell["text"])
                and not TIME_RE.fullmatch(cell["text"])
            ]
            if candidates:
                title = max(candidates, key=len)
        if title:
            event = _event(title, date_match.group(0), time_match.group(0), year, url)
            if event:
                events[event["event_id"]] = event

    # Current BLS pages also publish a list view: one visible release per line.
    if not events:
        lines = [" ".join(line.replace("\xa0", " ").split()) for line in "".join(parser.text_parts).splitlines()]
        for line in lines:
            date_match = DATE_RE.search(line)
            if not date_match:
                continue
            time_match = TIME_RE.search(line, date_match.end())
            if not time_match:
                continue
            title = line[time_match.end():].strip(" |\t:-")
            if not title or title.upper().startswith("NOTE:"):
                continue
            url = f"https://www.bls.gov/schedule/{year}/home.htm"
            for label, href in parser.links:
                if label.lower() in title.lower():
                    url = _absolute_url(href)
                    break
            event = _event(title, date_match.group(0), time_match.group(0), year, url)
            if event:
                events[event["event_id"]] = event

    return sorted(events.values(), key=lambda item: item["scheduled_at_utc"])


async def fetch_bls_calendar(client: httpx.AsyncClient, year: int) -> list[dict]:
    """Fetch official BLS release schedule. Fail visibly if its layout is unrecognized."""
    url = f"https://www.bls.gov/schedule/{year}/home.htm"
    response = await client.get(url, timeout=20)
    response.raise_for_status()
    events = parse_bls_schedule(response.text, year)
    if not events:
        raise ValueError(f"No BLS schedule events parsed from {url}; parser may need updating")
    return events
