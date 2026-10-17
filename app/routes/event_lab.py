"""Read-only API for historical event reaction statistics."""
from fastapi import APIRouter, Query

from ..db import get_db
from ..services.historical_event_lab import summarize_reactions

router = APIRouter()


@router.get("/api/research/event-lab")
def historical_event_lab(
    event_type: str | None = Query(default=None, max_length=100),
    instrument: str | None = Query(default=None, max_length=20),
):
    """Return descriptive 15-minute reactions from recorded observations."""
    clauses = []
    params: list[str] = []
    if event_type and event_type.strip():
        clauses.append("event_type = ?")
        params.append(event_type.strip())
    if instrument and instrument.strip():
        clauses.append("instrument = ?")
        params.append(instrument.strip().upper())
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_db() as db:
        rows = db.execute(
            "SELECT event_type, instrument, expected_direction, price_before, "
            "price_after_15m FROM macro_reactions" + where +
            " ORDER BY release_time DESC LIMIT 10000",
            params,
        ).fetchall()
    return {
        "source": "macro_reactions",
        "observations": len(rows),
        "results": summarize_reactions(dict(row) for row in rows),
        "limitations": [
            "Hanya memakai observasi yang dicatat atau diimpor pengguna.",
            "Tidak mengambil harga historis otomatis dan tidak mengukur slippage/spread.",
            "Statistik deskriptif bukan prediksi atau rekomendasi trading.",
            "Bias-aligned rate hanya bermakna jika bias benar-benar dicatat sebelum rilis.",
        ],
    }
