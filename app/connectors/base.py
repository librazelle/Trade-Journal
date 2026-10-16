from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import httpx


@dataclass
class NewsItem:
    external_id: str            # id unik dari sumber, dipakai untuk dedup
    source: str                 # nama tampilan, mis. "Federal Reserve"
    title: str
    published_at: datetime      # wajib timezone-aware (UTC)
    url: str | None = None
    summary: str | None = None  # ringkasan pendek saja, jangan isi artikel penuh
    tier: int = 2               # 1 = resmi, 2 = media terpercaya, 3 = konteks/agregator
    status: str = "reported"    # "official" | "reported" | "rumor"


class Connector(ABC):
    name: str = "base"
    interval_seconds: int = 60

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> list[NewsItem]:
        """Ambil item terbaru dari sumber. Dedup dilakukan oleh storage, bukan di sini."""
