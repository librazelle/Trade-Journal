"""Semua waktu disimpan dalam UTC dengan format sortable. Tampilan mengikuti display_tz."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .config import settings

UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"
MONTHS_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def fmt_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(UTC_FMT)


def parse_utc(value: str) -> datetime:
    return datetime.strptime(value, UTC_FMT).replace(tzinfo=timezone.utc)


def to_local(value: str | datetime) -> str:
    dt = value if isinstance(value, datetime) else parse_utc(value)
    local = dt.astimezone(ZoneInfo(settings.display_tz))
    return f"{local.day} {MONTHS_ID[local.month - 1]} {local:%H:%M}"
