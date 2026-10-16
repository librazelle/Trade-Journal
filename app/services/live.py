"""Broadcast in-process ke semua klien SSE yang sedang terhubung."""
from __future__ import annotations

import asyncio

_subscribers: set[asyncio.Queue] = set()


def subscribe() -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.add(queue)
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    _subscribers.discard(queue)


def publish(item: dict) -> None:
    for queue in list(_subscribers):
        try:
            queue.put_nowait(item)
        except asyncio.QueueFull:
            pass  # klien terlalu lambat, dibuang supaya worker tidak macet
