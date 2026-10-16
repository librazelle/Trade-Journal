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
from .services.econ_calendar import fetch_bls_calendar
from .services.calendar_store import ensure_calendar_table, save_calendar_events, list_calendar_events
from .timeutil import fmt_utc, to_local
from .worker import run_worker

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
def dashboard(request: Request):
    with get_db() as db:
        trades = db.execute("SELECT * FROM trades ORDER BY entry_time DESC LIMIT 50").fetchall()
        news = db.execute("SELECT * FROM news ORDER BY published_at DESC LIMIT 30").fetchall()
    now_local = datetime.now(ZoneInfo(settings.display_tz)).strftime("%Y-%m-%dT%H:%M")
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "trades": [dict(t) for t in trades],
            "news": [news_view(n) for n in news],
            "default_entry": now_local,
            "tz": settings.display_tz,
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
        # Historical/backfilled articles can have been published before entry but
        # ingested after the snapshot cutoff. Keep them visible for replay testing,
        # but label them as hindsight rather than information available to the trader.
        entry_dt = datetime.fromisoformat(row["entry_time"].replace("Z", "+00:00"))
        late_pre_entry = db.execute(
            """SELECT * FROM news
               WHERE published_at >= ?
                 AND published_at <= ?
                 AND ingested_at > ?
               ORDER BY published_at ASC LIMIT 200""",
            (
                fmt_utc(entry_dt - timedelta(hours=settings.lookback_hours)),
                row["entry_time"],
                fmt_utc(entry_dt + timedelta(minutes=1)),
            ),
        ).fetchall()
    trade = dict(row)
    context = [news_view(n) for n in json.loads(trade["context_json"])]
    economic_context = json.loads(trade.get("econ_context_json") or "[]")
    after_view = [news_view(n) for n in after]
    late_pre_entry_view = [news_view(n) for n in late_pre_entry]

    # Replay timeline is retrospective: pre-entry news is the frozen snapshot,
    # while post-entry news is explicitly marked as hindsight review material.
    replay_items = []
    for item in context:
        replay_items.append({
            "timestamp": item["published_at"],
            "time": item["published_at"],
            "published_at": item["published_at"],
            "ingested_at": item.get("ingested_at"),
            "kind": "news",
            "relation": "Sebelum entry · snapshot",
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
    for item in late_pre_entry_view:
        # This item was published before entry but arrived in our database later.
        # Never imply it was available at the time the trade was made.
        replay_items.append({
            "timestamp": item["published_at"],
            "time": item["published_at"],
            "published_at": item["published_at"],
            "ingested_at": item.get("ingested_at"),
            "kind": "news-retro-pre",
            "relation": "Terbit sebelum entry · masuk setelah cutoff (retrospektif)",
            "title": item["title"],
            "source": item["source"],
            "impact": item["impact"],
            "url": item.get("url"),
            "summary": item.get("summary"),
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
