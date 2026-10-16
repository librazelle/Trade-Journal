"""Tagging sederhana berbasis kata kunci dan skor dampak. Kontributor bisa menambah kata kunci di sini."""
from __future__ import annotations

import re

KEYWORDS: dict[str, list[str]] = {
    "gold": ["gold", "xau", "bullion"],
    "oil": ["oil", "crude", "wti", "brent", "opec"],
    "fed": ["fomc", "federal reserve", "powell", "rate decision", "interest rate"],
    "inflation": ["cpi", "ppi", "pce", "inflation"],
    "jobs": ["nonfarm", "payrolls", "unemployment", "jobs report"],
    "dollar": ["dollar", "dxy", "treasury yields", "yields"],
    "geopolitics": ["war", "iran", "israel", "ukraine", "russia", "sanctions", "missile", "conflict"],
    "trump": ["trump", "tariff", "tariffs"],
}


def tag_text(text: str) -> list[str]:
    low = text.lower()
    return [
        tag
        for tag, words in KEYWORDS.items()
        if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words)
    ]


def impact_score(tier: int, tags: list[str]) -> int:
    base = {1: 60, 2: 40}.get(tier, 20)
    return min(100, base + 8 * len(tags))
