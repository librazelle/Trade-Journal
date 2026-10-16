#!/usr/bin/env python3
"""Fetch a draft 2022-2025 macro release calendar from official US agency pages.

Sources: BLS yearly release calendars, BEA yearly schedules, Federal Reserve FOMC calendars.
All source calendar times are Eastern Time and are converted to UTC using zoneinfo.
Rows are tagged with source URLs and require review before trading research.
"""
from __future__ import annotations
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import pandas as pd
import requests

YEARS = range(2022, 2026)
ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
HEADERS = {"User-Agent": "Trade-Lens research calendar contact: local personal research"}
OUT = Path("tools/dukascopy/events_template.csv")


def get_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def local_to_utc(date_text: str, time_text: str) -> str | None:
    date_text = re.sub(r"\s+", " ", date_text.strip())
    time_text = re.sub(r"\s+", " ", time_text.strip()).upper()
    for fmt in ("%B %d, %Y %I:%M %p", "%b %d, %Y %I:%M %p",
                "%Y-%m-%d %I:%M %p"):
        try:
            dt = datetime.strptime(f"{date_text} {time_text}", fmt).replace(tzinfo=ET)
            return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return None


def extract_bls(year: int, release_name: str, event_type: str) -> list[dict]:
    url = f"https://www.bls.gov/schedule/{year}/"
    html = get_html(url)
    tables = pd.read_html(html)
    rows = []
    for table in tables:
        cols = [str(c).strip().lower() for c in table.columns]
        if not any("date" in c for c in cols) or not any("release" in c for c in cols):
            continue
        date_col = next(c for c in table.columns if "date" in str(c).lower())
        time_col = next((c for c in table.columns if "time" in str(c).lower()), None)
        release_col = next(c for c in table.columns if "release" in str(c).lower())
        for _, row in table.iterrows():
            title = str(row.get(release_col, ""))
            if release_name.lower() not in title.lower():
                continue
            date_text = str(row.get(date_col, "")).strip()
            time_text = str(row.get(time_col, "")).strip() if time_col else "08:30 AM"
            # BLS yearly calendars often have a date cell plus a time cell.
            date_match = re.search(r"([A-Za-z]+\s+\d{1,2},?\s*\d{4})", date_text)
            if not date_match:
                continue
            date_value = date_match.group(1).replace(",", "")
            utc = local_to_utc(date_value, time_text)
            if utc:
                rows.append({"event_type": event_type, "release_time_utc": utc,
                             "expected_direction": "", "notes": f"Official BLS calendar ET; verify | {url}"})
    return rows


def extract_bea(year: int) -> list[dict]:
    url = f"https://www.bea.gov/news/schedule/full-{year}"
    html = get_html(url)
    tables = pd.read_html(html)
    rows = []
    for table in tables:
        for _, row in table.iterrows():
            text = " ".join(str(x) for x in row.tolist())
            if "Personal Income and Outlays" not in text:
                continue
            # BEA schedule row commonly begins "January 31 8:30 AM".
            m = re.search(r"\b([A-Z][a-z]+)\s+(\d{1,2})\s+(\d{1,2}:\d{2}\s*[AP]M)\b", text)
            if not m:
                continue
            month, day, time_text = m.groups()
            utc = local_to_utc(f"{month} {day}, {year}", time_text)
            if utc:
                rows.append({"event_type": "PCE", "release_time_utc": utc,
                             "expected_direction": "", "notes": f"Official BEA schedule ET; verify | {url}"})
    return rows


def main() -> None:
    rows = []
    errors = []
    for year in YEARS:
        for label, event in (("Consumer Price Index", "CPI"),
                             ("Employment Situation", "NFP")):
            try:
                rows.extend(extract_bls(year, label, event))
            except Exception as exc:
                errors.append(f"BLS {year} {event}: {exc}")
        try:
            rows.extend(extract_bea(year))
        except Exception as exc:
            errors.append(f"BEA {year} PCE: {exc}")

    # FOMC statements are usually released at 2:00 PM ET on the second day
    # of scheduled meetings. Do not infer statement dates from meeting ranges:
    # add them from the official FOMC calendar after review.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=["event_type", "release_time_utc", "expected_direction", "notes"])
    if not df.empty:
        df = df.drop_duplicates(subset=["event_type", "release_time_utc"]).sort_values("release_time_utc")
    df.to_csv(OUT, index=False)
    print(f"Saved {len(df)} candidate CPI/NFP/PCE rows to {OUT}")
    print("FOMC is intentionally not auto-filled: verify statement dates/times on the Fed calendar.")
    print("IMPORTANT: review all rows and confirm year parsing before using for analysis.")
    if errors:
        print("\nSome official calendars could not be parsed:")
        print("\n".join(errors))
    print("Official FOMC calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")


if __name__ == "__main__":
    main()
