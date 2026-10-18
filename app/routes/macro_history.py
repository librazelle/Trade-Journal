"""Import historical macro-event reactions from a user-supplied CSV."""
import csv
import io
import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import RedirectResponse, Response

from ..config import settings
from ..db import get_db
from ..timeutil import fmt_utc

router = APIRouter()
ALLOWED_INSTRUMENTS = {
    "XAUUSD", "NASDAQ100", "S&P500", "US30", "DXY", "US10Y",
    "USOIL", "EURUSD", "USDJPY", "BTCUSD",
}
REQUIRED_COLUMNS = {
    "event_type", "instrument", "release_time", "expected_direction",
    "price_before", "price_after_15m",
}


@router.get("/macro-reactions/template.csv")
def macro_history_template():
    content = (
        "event_type,instrument,release_time,expected_direction,price_before,price_after_1m,price_after_5m,price_after_15m,price_after_60m,note\n"
    )
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="macro-reactions-template.csv"'},
    )


@router.post("/macro-reactions/import")
async def import_macro_history(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Unggah file .csv")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, "Ukuran CSV maksimal 5 MB")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise HTTPException(400, "Kolom CSV kurang: " + ", ".join(sorted(missing)))
        rows = list(reader)
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV harus memakai encoding UTF-8") from None
    if len(rows) > 10000:
        raise HTTPException(400, "Maksimal 10.000 baris per impor")

    inserted = 0
    skipped = 0
    errors = []
    with get_db() as db:
        for line, row in enumerate(rows, start=2):
            try:
                event = (row.get("event_type") or "").strip()
                instrument = (row.get("instrument") or "").strip().upper()
                direction = (row.get("expected_direction") or "").strip().lower()
                raw_time = (row.get("release_time") or "").strip()
                if not event or len(event) > 100:
                    raise ValueError("event_type kosong atau terlalu panjang")
                if instrument not in ALLOWED_INSTRUMENTS:
                    raise ValueError("instrument tidak valid")
                if direction not in {"up", "down"}:
                    raise ValueError("expected_direction harus up atau down")
                release_dt = datetime.fromisoformat(raw_time)
                if release_dt.tzinfo is None:
                    release_dt = release_dt.replace(tzinfo=ZoneInfo(settings.display_tz))
                release_time = fmt_utc(release_dt.astimezone(timezone.utc))
                before = float((row.get("price_before") or "").strip().replace(",", "."))
                after = float((row.get("price_after_15m") or "").strip().replace(",", "."))
                def optional_price(column):
                    raw = (row.get(column) or "").strip()
                    if not raw:
                        return None
                    value = float(raw.replace(",", "."))
                    if not math.isfinite(value) or value <= 0:
                        raise ValueError(f"{column} harus berupa angka positif yang valid")
                    return value
                after_1m = optional_price("price_after_1m")
                after_5m = optional_price("price_after_5m")
                after_60m = optional_price("price_after_60m")
                if not math.isfinite(before) or not math.isfinite(after):
                    raise ValueError("harga harus berupa angka finite yang valid")
                if before <= 0 or after <= 0:
                    raise ValueError("harga harus lebih dari nol")
                exists = db.execute(
                    "SELECT 1 FROM macro_reactions WHERE event_type=? AND instrument=? AND release_time=? LIMIT 1",
                    (event, instrument, release_time),
                ).fetchone()
                if exists:
                    skipped += 1
                    continue
                note = (row.get("note") or "").strip()
                note = ("[HISTORICAL CSV] " + note).strip()
                db.execute(
                    """INSERT INTO macro_reactions
                       (event_type, instrument, release_time, expected_direction,
                        price_before, price_after_1m, price_after_5m, price_after_15m,
                        price_after_60m, note, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (event, instrument, release_time, direction, before, after_1m, after_5m,
                     after, after_60m, note, fmt_utc(datetime.now(timezone.utc))),
                )
                inserted += 1
            except (ValueError, TypeError) as exc:
                errors.append(f"Baris {line}: {exc}")
                if len(errors) >= 10:
                    break
        if errors:
            # Keep valid rows from the same file, but show the user which rows were rejected.
            pass
    if errors:
        detail = f"Impor selesai sebagian: {inserted} ditambahkan, {skipped} duplikat dilewati. " + " | ".join(errors)
        # Redirect query string is displayed by the dashboard status banner.
        from urllib.parse import quote
        return RedirectResponse("/?macro_import=" + quote(detail), status_code=303)
    from urllib.parse import quote
    return RedirectResponse(
        "/?macro_import=" + quote(f"Impor selesai: {inserted} baris ditambahkan, {skipped} duplikat dilewati."),
        status_code=303,
    )
