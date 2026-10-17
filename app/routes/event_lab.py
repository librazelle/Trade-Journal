"""Read-only API and curated external research page."""
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from ..db import get_db
from ..services.historical_event_lab import summarize_reactions

router = APIRouter()

# Publicly displayed aggregate statistics; kept separate from the app's +15m observations.
EXTERNAL = [
    ("US CPI", "https://tradingnews24.com/research/xauusd/us-cpi/", "Jul 2019–May 2026", 75, "0.881%", "1.903%", "2.417%", "0.560%", "57.3% naik / 42.7% turun"),
    ("US Core PCE", "https://tradingnews24.com/research/xauusd/us-core-pce/", "Jul 2019–Apr 2026", 75, "0.622%", "1.201%", "2.935%", None, None),
    ("US Non-Farm Payrolls", "https://tradingnews24.com/research/xauusd/us-nfp/", "Jul 2019–May 2026", 74, "1.076%", "1.814%", "2.653%", "0.669%", "52.7% naik / 47.3% turun"),
]


@router.get("/research", response_class=HTMLResponse)
def external_research_library():
    cards = []
    for event, url, period, n, typical, p90, maximum, close_abs, direction in EXTERNAL:
        close_html = f"<p><b>Median perubahan absolut saat penutupan:</b> {close_abs}</p>" if close_abs else ""
        direction_html = f"<p><b>Arah penutupan:</b> {direction}</p>" if direction else ""
        cards.append(
            f'<article class="card"><small>XAUUSD · 4H setelah rilis · N={n}</small>'
            f'<h2>{event}</h2><p class="muted">Periode studi: {period} · snapshot 17 Okt 2026</p>'
            f'<div class="metrics"><div><span>Peak tipikal</span><b>{typical}</b></div>'
            f'<div><span>Puncak P90</span><b>{p90}</b></div><div><span>Ekstrem historis</span><b>{maximum}</b></div></div>'
            f'{close_html}{direction_html}<p><a href="{url}" target="_blank" rel="noopener noreferrer">Buka tabel rilis dan metodologi asli ↗</a></p></article>'
        )
    cards_html = "".join(cards)
    return HTMLResponse(
        '<!doctype html><html lang="id"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>External Research · Trade-Lens</title><link rel="stylesheet" href="/static/style.css">'
        '<style>.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:14px}'
        '.card{background:var(--surface);border:1px solid var(--rule);padding:15px;min-width:0}'
        '.card small{color:var(--long)}.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:14px 0}'
        '.metrics div{background:var(--bg);padding:8px;border:1px solid var(--rule)}.metrics span{display:block;font-size:11px;color:var(--muted)}'
        '.metrics b{display:block;font-size:18px;margin-top:4px}.warning{border-left:3px solid var(--rumor);padding:10px;background:var(--surface)}</style>'
        '</head><body><header class="topbar"><a class="brand" href="/">trade-lens</a><span class="tz">External Research</span></header>'
        '<main class="wrap"><p><a href="/">← Kembali ke dashboard</a></p><h1>External Research Library</h1>'
        '<p class="muted">Ringkasan riset historis publik untuk XAUUSD. Sumber: TradingNews24.</p>'
        '<p class="warning">Ini snapshot statistik publik, bukan feed live atau data trade mentah. Peak excursion mengukur gerak maksimum dua arah dalam jendela waktu, bukan profit yang pasti bisa ditangkap. Jangan gabungkan dengan statistik internal +15 menit: horizon dan metodologinya berbeda.</p>'
        f'<section class="grid">{cards_html}</section>'
        '<section class="section"><h2>Batasan</h2><ul>'
        '<li>Angka di bawah adalah statistik agregat dari sumber, bukan perhitungan Trade-Lens.</li>'
        '<li>Riset tidak mengondisikan hasil pada surprise actual-vs-forecast, rezim pasar, spread, slippage, atau aturan entry TJR/CISD.</li>'
        '<li>Belum ada baris per rilis yang diimpor ke tabel internal. Link membuka tabel lengkap dan metodologi asli.</li></ul>'
        '<p class="muted">Metodologi: <a href="https://tradingnews24.com/research/methodology/event-intelligence/" target="_blank" rel="noopener noreferrer">Event Intelligence ↗</a> · '
        'Jadwal resmi CPI: <a href="https://www.bls.gov/schedule/news_release/cpi.htm" target="_blank" rel="noopener noreferrer">BLS ↗</a></p></section></main></body></html>'
    )


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
