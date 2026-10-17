"""Entry point. Jalankan: uvicorn app.main:app --workers 1"""
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .db import get_db, init_db
from .services import live
from .services.context import build_context
from .services.economic_context import build_economic_context
from .services.news import news_view
from .services.news_relevance import high_impact_news
from .services.econ_calendar import fetch_bls_calendar
from .services.calendar_store import ensure_calendar_table, save_calendar_events, list_calendar_events
from .timeutil import fmt_utc, to_local
from .worker import run_worker
from .services.source_health import snapshot as source_health_snapshot
from .routes.macro_history import router as macro_history_router

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["to_local"] = to_local


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    worker = asyncio.create_task(run_worker()) if settings.enable_worker else None
    yield
    if worker:
        worker.cancel()


app = FastAPI(title="trade-lens", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(macro_history_router)


# ---------- helper input ----------

def _parse_float(value: str, label: str, required: bool = False) -> float | None:
    value = (value or "").strip().replace(",", ".")
    if not value:
        if required:
            raise HTTPException(400, f"{label} wajib diisi")
        return None
    try:
        return float(value)
    except ValueError:
        raise HTTPException(400, f"{label} harus berupa angka") from None


def _local_to_utc(value: str) -> datetime:
    try:
        naive = datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, "Format waktu entry tidak valid") from None
    return naive.replace(tzinfo=ZoneInfo(settings.display_tz)).astimezone(timezone.utc)


# ---------- halaman ----------

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, macro_import: str | None = None):
    with get_db() as db:
        trades = db.execute("SELECT * FROM trades ORDER BY entry_time DESC LIMIT 50").fetchall()
        news = db.execute("SELECT * FROM news ORDER BY published_at DESC LIMIT 100").fetchall()
        reactions = db.execute("SELECT * FROM macro_reactions ORDER BY release_time DESC LIMIT 20").fetchall()
        reaction_stats = db.execute(
            """SELECT event_type, instrument, COUNT(*) AS samples,
                      SUM(CASE
                          WHEN (expected_direction = 'up' AND price_after_15m > price_before)
                            OR (expected_direction = 'down' AND price_after_15m < price_before)
                          THEN 1 ELSE 0 END) AS aligned
               FROM macro_reactions
               GROUP BY event_type, instrument
               ORDER BY samples DESC, event_type, instrument"""
        ).fetchall()
    news_views = [news_view(n) | {"tier": n["tier"]} for n in news]
    priority_news = high_impact_news(news_views, limit=5)
    # Keep the normal dashboard feed concise while ranking macro-sensitive headlines separately.
    news_views = news_views[:30]
    now_local = datetime.now(ZoneInfo(settings.display_tz)).strftime("%Y-%m-%dT%H:%M")
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "trades": [dict(t) for t in trades],
            "news": news_views,
            "priority_news": priority_news,
            "macro_reactions": [dict(r) for r in reactions],
            "reaction_stats": [
                {**dict(r), "win_rate": round(100 * r["aligned"] / r["samples"], 1)}
                for r in reaction_stats
            ],
            "default_entry": now_local,
            "tz": settings.display_tz,
            "macro_import_message": macro_import,
        },
    )


@app.get("/trades/{trade_id}", response_class=HTMLResponse)
def trade_detail(request: Request, trade_id: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Trade tidak ditemukan")
        after = db.execute(
            "SELECT * FROM news WHERE published_at > ? ORDER BY published_at DESC LIMIT 200",
            (row["entry_time"],),
        ).fetchall()
        # Fetch every article published in the pre-entry lookback window. The
        # replay view will classify it using ingested_at, rather than hiding late data.
        entry_dt = datetime.fromisoformat(row["entry_time"].replace("Z", "+00:00"))
        pre_entry_news = db.execute(
            """SELECT * FROM news
               WHERE published_at >= ?
                 AND published_at <= ?
               ORDER BY published_at ASC LIMIT 200""",
            (
                fmt_utc(entry_dt - timedelta(hours=settings.lookback_hours)),
                row["entry_time"],
            ),
        ).fetchall()
    trade = dict(row)
    context = [news_view(n) for n in json.loads(trade["context_json"])]
    economic_context = json.loads(trade.get("econ_context_json") or "[]")
    after_view = [news_view(n) for n in after]
    pre_entry_news_view = [news_view(n) for n in pre_entry_news]

    # Replay timeline is retrospective: pre-entry news is the frozen snapshot,
    # while post-entry news is explicitly marked as hindsight review material.
    replay_items = []
    cutoff_utc = fmt_utc(datetime.fromisoformat(trade["entry_time"].replace("Z", "+00:00")) + timedelta(minutes=1))
    for item in pre_entry_news_view:
        known_by_entry = item.get("ingested_at") and item["ingested_at"] <= cutoff_utc
        replay_items.append({
            "timestamp": item["published_at"],
            "time": item["published_at"],
            "published_at": item["published_at"],
            "ingested_at": item.get("ingested_at"),
            "kind": "news" if known_by_entry else "news-retro-pre",
            "relation": "Sebelum entry · snapshot" if known_by_entry else "Terbit sebelum entry · masuk setelah cutoff (retrospektif)",
            "title": item["title"],
            "source": item["source"],
            "impact": item["impact"],
            "url": item.get("url"),
            "summary": item.get("summary"),
        })
    for event in economic_context:
        replay_items.append({
            "timestamp": event["scheduled_at_utc"],
            "time": event["scheduled_at_utc"],
            "kind": "calendar",
            "relation": "Event terjadwal · diketahui saat entry",
            "title": event["name"],
            "source": event["source"],
            "impact": event["impact"],
            "url": event.get("url"),
            "summary": None,
        })
    for item in after_view:
        replay_items.append({
            "timestamp": item["published_at"],
            "time": item["published_at"],
            "published_at": item["published_at"],
            "ingested_at": item.get("ingested_at"),
            "kind": "news-after",
            "relation": "Setelah entry · tinjauan retrospektif",
            "title": item["title"],
            "source": item["source"],
            "impact": item["impact"],
            "url": item.get("url"),
            "summary": item.get("summary"),
        })
    replay_items.sort(key=lambda item: item["timestamp"])

    return templates.TemplateResponse(
        request,
        "trade.html",
        {
            "trade": trade,
            "context": context,
            "economic_context": economic_context,
            "after": after_view,
            "replay_items": replay_items,
            "lookback": settings.lookback_hours,
            "tz": settings.display_tz,
        },
    )


# ---------- aksi ----------

@app.post("/macro-reactions")
def create_macro_reaction(
    event_type: str = Form(...),
    instrument: str = Form(...),
    release_time: str = Form(...),
    expected_direction: str = Form(...),
    price_before: str = Form(...),
    price_after_15m: str = Form(...),
    note: str = Form(""),
):
    event_type = event_type.strip()
    instrument = instrument.strip().upper()
    if not event_type or len(event_type) > 100:
        raise HTTPException(400, "Nama event wajib diisi (maksimal 100 karakter)")
    allowed_instruments = {
        "XAUUSD", "NASDAQ100", "S&P500", "US30", "DXY", "US10Y",
        "USOIL", "EURUSD", "USDJPY", "BTCUSD",
    }
    if instrument not in allowed_instruments:
        raise HTTPException(400, "Instrumen tidak valid")
    if expected_direction not in ("up", "down"):
        raise HTTPException(400, "Bias harus naik atau turun")
    before = _parse_float(price_before, "Harga sebelum rilis", required=True)
    after = _parse_float(price_after_15m, "Harga 15 menit setelah rilis", required=True)
    if before <= 0 or after <= 0:
        raise HTTPException(400, "Harga harus lebih dari nol")
    release_utc = _local_to_utc(release_time)
    with get_db() as db:
        db.execute(
            """INSERT INTO macro_reactions
               (event_type, instrument, release_time, expected_direction,
                price_before, price_after_15m, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_type, instrument, fmt_utc(release_utc), expected_direction,
             before, after, note.strip(), fmt_utc(datetime.now(timezone.utc))),
        )
    return RedirectResponse("/", status_code=303)


@app.post("/trades")
def create_trade(
    instrument: str = Form("XAUUSD"),
    direction: str = Form(...),
    entry_price: str = Form(...),
    entry_time: str = Form(...),
    lot: str = Form(""),
    sl: str = Form(""),
    tp: str = Form(""),
    note: str = Form(""),
):
    if direction not in ("long", "short"):
        raise HTTPException(400, "Arah harus long atau short")
    price = _parse_float(entry_price, "Harga entry", required=True)
    if price <= 0:
        raise HTTPException(400, "Harga entry harus lebih dari 0")

    entry_utc = _local_to_utc(entry_time)
    now = datetime.now(timezone.utc)
    # datetime-local inputs have minute precision. Allow that minute for the
    # snapshot cutoff, but never include data fetched after the entry minute.
    known_at = min(now, entry_utc + timedelta(minutes=1))
    context = build_context(entry_utc, known_at=known_at)
    economic_context = build_economic_context(entry_utc, known_at=known_at)

    with get_db() as db:
        cur = db.execute(
            """INSERT INTO trades
               (instrument, direction, entry_price, entry_time, lot, sl, tp, note,
                context_json, econ_context_json, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                instrument.strip().upper() or "XAUUSD",
                direction,
                price,
                fmt_utc(entry_utc),
                _parse_float(lot, "Lot"),
                _parse_float(sl, "SL"),
                _parse_float(tp, "TP"),
                note.strip(),
                json.dumps(context),
                json.dumps(economic_context),
                fmt_utc(now),
            ),
        )
        trade_id = cur.lastrowid
    return RedirectResponse(f"/trades/{trade_id}", status_code=303)


@app.post("/trades/{trade_id}/delete")
def delete_trade(trade_id: int):
    with get_db() as db:
        db.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
    return RedirectResponse("/", status_code=303)


# ---------- realtime & kesehatan ----------


# ---------- penjelasan berita AI ----------
_ai_request_times: dict[str, list[float]] = {}


@app.post("/api/news/{news_id}/explain")
async def explain_news_endpoint(news_id: int, request: Request):
    """Generate once per article, then serve the cached beginner-friendly explanation."""
    import time
    import httpx
    from .services.ai_news_explainer import explain_news_with_ai

    with get_db() as db:
        row = db.execute(
            "SELECT id, source, title, url, summary FROM news WHERE id = ?",
            (news_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Berita tidak ditemukan")
        cached = db.execute(
            "SELECT explanation, model FROM news_ai_summaries WHERE news_id = ?",
            (news_id,),
        ).fetchone()
    if cached:
        return {"news_id": news_id, "explanation": cached["explanation"], "cached": True, "model": cached["model"]}
    if not settings.huggingface_token:
        raise HTTPException(503, "Fitur AI belum dikonfigurasi. Admin perlu mengisi HF_TOKEN di environment server.")

    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = [stamp for stamp in _ai_request_times.get(client_ip, []) if now - stamp < 60]
    if len(recent) >= 10:
        raise HTTPException(429, "Batas permintaan penjelasan AI tercapai. Coba lagi sebentar.")
    recent.append(now)
    _ai_request_times[client_ip] = recent

    try:
        explanation = await explain_news_with_ai(
            title=row["title"],
            source=row["source"],
            summary=row["summary"] or "",
            url=row["url"],
        )
    except RuntimeError as exc:
        if str(exc) == "AI_NOT_CONFIGURED":
            raise HTTPException(503, "Fitur AI belum dikonfigurasi.") from None
        raise HTTPException(502, "Layanan AI belum bisa memproses berita ini.") from None
    except httpx.TimeoutException:
        raise HTTPException(504, "AI terlalu lama merespons. Coba lagi.") from None
    except httpx.HTTPStatusError as exc:
        # Log provider response details for diagnosis, but never log request headers or secrets.
        provider_body = (exc.response.text or "")[:800].replace("\\n", " ")
        import logging
        logging.getLogger(__name__).warning(
            "Hugging Face inference returned HTTP %s: %s",
            exc.response.status_code,
            provider_body,
        )
        if exc.response.status_code == 429:
            raise HTTPException(429, "Batas gratis Hugging Face tercapai atau model sedang membatasi permintaan. Coba lagi nanti.") from None
        if exc.response.status_code in (401, 403):
            raise HTTPException(503, "Token Hugging Face tidak valid atau model tidak memiliki akses.") from None
        raise HTTPException(502, "Layanan AI sedang bermasalah.") from None
    except (httpx.HTTPError, ValueError) as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Hugging Face inference request failed (%s): %s",
            type(exc).__name__,
            str(exc)[:500],
        )
        raise HTTPException(502, "Gagal mengambil penjelasan dari layanan AI.") from None

    created_at = fmt_utc(datetime.now(timezone.utc))
    with get_db() as db:
        db.execute(
            """INSERT INTO news_ai_summaries (news_id, explanation, model, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(news_id) DO UPDATE SET
                 explanation=excluded.explanation, model=excluded.model, created_at=excluded.created_at""",
            (news_id, explanation, settings.ai_model, created_at),
        )
    return {"news_id": news_id, "explanation": explanation, "cached": False, "model": settings.ai_model}


@app.get("/stream/news")
async def stream_news(request: Request):
    queue = live.subscribe()
    item_template = templates.get_template("partials/news_item.html")

    async def event_source():
        try:
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    row = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                html = item_template.render(item=news_view(row))
                html = " ".join(html.split())  # satu baris agar aman untuk SSE
                yield f"event: news\ndata: {html}\n\n"
        finally:
            live.unsubscribe(queue)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/source-health")
def source_health():
    """Current in-memory polling status for official RSS connectors."""
    labels = {
        "fed_rss": "Federal Reserve",
        "bls_rss": "U.S. Bureau of Labor Statistics",
        "bbc_world_rss": "BBC News · World",
        "bbc_business_rss": "BBC News · Business",
        "guardian_world_rss": "The Guardian · World",
        "guardian_business_rss": "The Guardian · Business",
    }
    return {
        "checked_at": fmt_utc(datetime.now(timezone.utc)),
        "sources": [
            {**item, "label": labels.get(item["name"], item["name"])}
            for item in source_health_snapshot()
        ],
    }


@app.get("/api/calendar")
async def economic_calendar(year: int | None = None):
    """Official BLS release calendar; cached results survive temporary source failures."""
    import httpx

    current_year = datetime.now(timezone.utc).year
    selected_year = year or current_year
    if selected_year < current_year - 1 or selected_year > current_year + 2:
        raise HTTPException(400, "Tahun kalender harus berada dalam rentang tahun berjalan -1 sampai +2")

    ensure_calendar_table()
    cached = list_calendar_events(selected_year)
    cache_cutoff = fmt_utc(datetime.now(timezone.utc) - timedelta(hours=6))
    if cached and min(row["fetched_at"] for row in cached) >= cache_cutoff:
        return {
            "year": selected_year,
            "source": "U.S. Bureau of Labor Statistics",
            "source_url": f"https://www.bls.gov/schedule/{selected_year}/home.htm",
            "timezone_source": "America/New_York",
            "timezone_output": "UTC",
            "stale": False,
            "events": cached,
        }

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent, "Accept": "text/html"},
            follow_redirects=True,
        ) as client:
            events = await fetch_bls_calendar(client, selected_year)
        save_calendar_events(events)
        cached = list_calendar_events(selected_year)
        return {
            "year": selected_year,
            "source": "U.S. Bureau of Labor Statistics",
            "source_url": f"https://www.bls.gov/schedule/{selected_year}/home.htm",
            "timezone_source": "America/New_York",
            "timezone_output": "UTC",
            "stale": False,
            "events": cached,
        }
    except (httpx.HTTPError, ValueError):
        cached = list_calendar_events(selected_year)
        if cached:
            return {
                "year": selected_year,
                "source": "U.S. Bureau of Labor Statistics",
                "source_url": f"https://www.bls.gov/schedule/{selected_year}/home.htm",
                "timezone_source": "America/New_York",
                "timezone_output": "UTC",
                "stale": True,
                "events": cached,
            }
        raise HTTPException(502, "Kalender BLS tidak tersedia dan belum ada cache lokal") from None
