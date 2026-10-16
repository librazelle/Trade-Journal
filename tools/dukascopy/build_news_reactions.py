#!/usr/bin/env python3
"""Build XAUUSD news-reaction rows from Dukascopy M1 candles and a release calendar.

Input candle CSV: Date, Open, High, Low, Close, Volume (Date must include time).
Input event CSV: event_type,release_time_utc,expected_direction,notes
release_time_utc must be ISO-like UTC, e.g. 2025-01-15 13:30:00.
This script measures observed price reaction, not a pre-news forecast.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import pandas as pd

HORIZONS = (5, 15, 30, 60)
EVENT_COLUMNS = ["event_type", "release_time_utc", "expected_direction", "notes"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candles", required=True, help="Path to Dukascopy M1 CSV")
    parser.add_argument("--events", default="tools/dukascopy/events_template.csv",
                        help="CSV containing official release timestamps in UTC")
    parser.add_argument("--output", default="tools/dukascopy/news_reactions.csv")
    args = parser.parse_args()

    candle_path = Path(args.candles)
    event_path = Path(args.events)
    if not candle_path.exists():
        print(f"ERROR: candle file not found: {candle_path}", file=sys.stderr)
        return 2
    if not event_path.exists():
        event_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([
            {"event_type": "CPI", "release_time_utc": "2025-01-15 13:30:00",
             "expected_direction": "", "notes": "REPLACE with verified official timestamp"},
            {"event_type": "NFP", "release_time_utc": "", "expected_direction": "",
             "notes": ""},
            {"event_type": "PCE", "release_time_utc": "", "expected_direction": "",
             "notes": ""},
            {"event_type": "FOMC", "release_time_utc": "", "expected_direction": "",
             "notes": ""},
        ], columns=EVENT_COLUMNS).to_csv(event_path, index=False)
        print(f"Created event template: {event_path}")
        print("Fill it with VERIFIED release timestamps in UTC, then rerun.")
        print("The example CPI row is explicitly a placeholder and must be replaced.")
        return 0

    candles = pd.read_csv(candle_path)
    candles.columns = [str(c).strip() for c in candles.columns]
    date_col = next((c for c in candles.columns if c.lower() in ("date", "datetime", "timestamp", "time")), None)
    close_col = next((c for c in candles.columns if c.lower() == "close"), None)
    if not date_col or not close_col:
        print(f"ERROR: need timestamp and Close columns. Found: {list(candles.columns)}", file=sys.stderr)
        return 2

    candles["_time"] = pd.to_datetime(candles[date_col], utc=True, errors="coerce")
    candles["_close"] = pd.to_numeric(candles[close_col], errors="coerce")
    candles = candles.dropna(subset=["_time", "_close"]).sort_values("_time").drop_duplicates("_time")
    if candles.empty:
        print("ERROR: no valid timestamp/Close rows found.", file=sys.stderr)
        return 2
    times = candles["_time"]
    prices = candles["_close"]
    events = pd.read_csv(event_path)
    if "event_type" not in events.columns or "release_time_utc" not in events.columns:
        print("ERROR: event CSV needs event_type and release_time_utc columns.", file=sys.stderr)
        return 2

    out = []
    for _, ev in events.iterrows():
        raw_time = ev.get("release_time_utc")
        if pd.isna(raw_time) or not str(raw_time).strip():
            continue
        release = pd.to_datetime(raw_time, utc=True, errors="coerce")
        if pd.isna(release):
            print(f"Skipping invalid timestamp: {raw_time}")
            continue
        # Use last candle at or before release as baseline. Horizons use first candle
        # at or after release + N minutes, avoiding accidental look-ahead in baseline.
        base_idx = times.searchsorted(release, side="right") - 1
        if base_idx < 0:
            print(f"Skipping event before available history: {release}")
            continue
        base_price = float(prices.iloc[base_idx])
        row = {
            "event_type": str(ev.get("event_type", "")).strip().upper(),
            "release_time_utc": release.isoformat(),
            "baseline_time_utc": times.iloc[base_idx].isoformat(),
            "price_before": base_price,
            "expected_direction": str(ev.get("expected_direction", "") or "").strip().lower(),
            "notes": str(ev.get("notes", "") or ""),
        }
        for mins in HORIZONS:
            target = release + pd.Timedelta(minutes=mins)
            idx = times.searchsorted(target, side="left")
            if idx >= len(times) or times.iloc[idx] > target + pd.Timedelta(minutes=3):
                row[f"price_after_{mins}m"] = None
                row[f"change_{mins}m"] = None
                row[f"change_pct_{mins}m"] = None
                row[f"reaction_{mins}m"] = "missing"
                continue
            price = float(prices.iloc[idx])
            change = price - base_price
            row[f"price_after_{mins}m"] = price
            row[f"change_{mins}m"] = change
            row[f"change_pct_{mins}m"] = (change / base_price * 100) if base_price else None
            row[f"reaction_{mins}m"] = "up" if change > 0 else "down" if change < 0 else "flat"
            row[f"candle_time_{mins}m_utc"] = times.iloc[idx].isoformat()
        out.append(row)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out).to_csv(output, index=False)
    print(f"Saved {len(out)} event reactions to {output}")
    print(f"Loaded {len(candles):,} valid M1 candles from {times.iloc[0]} to {times.iloc[-1]}")
    print("Reminder: these are observed post-release reactions, not predictive bias accuracy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
