"""Worker background: polling semua connector, menyimpan item baru, lalu menyiarkannya."""
from __future__ import annotations

import asyncio
import logging

import httpx

from .config import settings
from .connectors import CONNECTORS
from .connectors.base import Connector
from .services import live
from .services.news import save_items
from .services.source_health import record_poll

log = logging.getLogger("trade_lens.worker")


async def _poll(connector: Connector, client: httpx.AsyncClient) -> None:
    first_run = True
    while True:
        try:
            items = await connector.fetch(client)
            new_rows = await asyncio.to_thread(save_items, items)
            record_poll(connector.name, True, len(items), new_rows)
            if new_rows:
                log.info("%s: %d item baru", connector.name, len(new_rows))
            # Pada run pertama, item lama hanya disimpan. Tidak disiarkan sebagai "live".
            if not first_run:
                for row in new_rows:
                    live.publish(row)
            first_run = False
        except Exception as exc:
            record_poll(connector.name, False, error=f"{type(exc).__name__}: {exc}")
            log.exception("connector %s gagal, dicoba lagi", connector.name)
        await asyncio.sleep(connector.interval_seconds)


async def run_worker() -> None:
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        await asyncio.gather(*(_poll(c, client) for c in CONNECTORS))
