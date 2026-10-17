"""Transparent rule-based news relevance scorecard.

This module scores topic relevance, not price direction or probability. Rules and
labels are deliberately inspectable so users can challenge false positives.
"""
from __future__ import annotations

import re


ASSET_RULES = {
    "XAUUSD": {
        "high": ("gold", "xauusd", "bullion", "precious metal", "real yield", "treasury yield", "central bank gold"),
        "medium": ("inflation", "cpi", "pce", "fomc", "federal reserve", "interest rate", "dollar", "dxy", "sanction", "geopolitical", "war", "safe haven"),
    },
    "NASDAQ100": {
        "high": ("nasdaq", "technology stocks", "tech stocks", "megacap", "semiconductor", "earnings"),
        "medium": ("fomc", "federal reserve", "interest rate", "treasury yield", "bond yield", "inflation", "cpi", "pce", "gdp", "recession", "employment", "payroll", "tariff"),
    },
    "DXY": {
        "high": ("dxy", "dollar index", "us dollar", "u.s. dollar", "federal reserve", "fomc", "fed funds rate"),
        "medium": ("inflation", "cpi", "pce", "payroll", "employment", "gdp", "treasury yield", "interest rate", "risk aversion"),
    },
}

EVENT_RULES = [
    ("Kebijakan moneter", ("fomc", "federal reserve", "fed funds rate", "rate decision", "interest rate", "powell")),
    ("Inflasi", ("consumer price index", "cpi", "producer price index", "ppi", "pce", "inflation")),
    ("Tenaga kerja", ("nonfarm payroll", "payroll", "unemployment", "employment situation", "jobless claims")),
    ("Pertumbuhan ekonomi", ("gdp", "gross domestic product", "retail sales", "economic growth", "recession")),
    ("Geopolitik/perdagangan", ("sanction", "tariff", "trade war", "geopolitical", "war", "missile", "conflict", "ceasefire")),
    ("Energi", ("crude oil", "brent", "wti", "opec", "natural gas", "energy")),
]


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").lower()).strip()


def _matches(text: str, keywords: tuple[str, ...]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]


def build_news_scorecard(title: str, summary: str = "", source: str = "", tier: int | None = None) -> dict:
    """Build explainable relevance labels; no directional call and no fake probabilities."""
    text = _normalise(f"{title or ''} {summary or ''}")
    event_type = "Belum terklasifikasi"
    matched_event = []
    for label, keywords in EVENT_RULES:
        matched_event = _matches(text, keywords)
        if matched_event:
            event_type = label
            break

    assets = {}
    any_match = False
    for asset, rules in ASSET_RULES.items():
        high = _matches(text, rules["high"])
        medium = _matches(text, rules["medium"])
        if high:
            level, evidence = "Tinggi", high[:3]
        elif medium:
            level, evidence = "Sedang", medium[:3]
        else:
            level, evidence = "Rendah / belum jelas", []
        any_match = any_match or bool(evidence)
        assets[asset] = {
            "relevance": level,
            "matched_terms": evidence,
            "reason": (
                "Ada istilah yang secara langsung terkait dengan instrumen." if high else
                "Ada jalur makro tidak langsung yang mungkin relevan." if medium else
                "Judul/ringkasan tidak menunjukkan kaitan spesifik yang cukup."
            ),
        }

    source_text = _normalise(source)
    official = bool(tier == 1 or any(term in source_text for term in ("federal reserve", "bureau of labor", "bls.gov", "treasury.gov", "bea.gov", "official")))
    detail_count = len(_normalise(summary).split())
    if official and detail_count >= 30:
        evidence_quality = "Sedang–tinggi"
        evidence_note = "Sumber tampak resmi dan ringkasan menyediakan konteks; verifikasi isi asli tetap diperlukan."
    elif official or detail_count >= 30:
        evidence_quality = "Sedang"
        evidence_note = "Ada sebagian indikator kredibilitas/konteks, tetapi informasi yang tersedia belum cukup untuk kesimpulan kuat."
    else:
        evidence_quality = "Rendah–sedang"
        evidence_note = "Penilaian hanya memakai metadata dan ringkasan pendek; cek sumber asli sebelum menarik kesimpulan."

    return {
        "event_type": event_type,
        "relevance": assets,
        "evidence_quality": evidence_quality,
        "evidence_note": evidence_note,
        "direction": "Belum ditentukan",
        "direction_note": "Relevansi bukan arah harga. Arah memerlukan detail berita, ekspektasi pasar, dan konfirmasi data/harga.",
        "matched_event_terms": matched_event[:3],
        "method": "Heuristik kata kunci yang transparan; bukan model statistik, korelasi terukur, atau sinyal trading.",
        "version": "scorecard-v1",
    }
