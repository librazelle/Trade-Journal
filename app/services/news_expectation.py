"""Free, transparent macro-release interpretation.

This module does not fetch or invent consensus forecasts. It interprets values only
when supplied by a source or entered by the user, and keeps macro bias distinct
from confirmed market direction.
"""
from __future__ import annotations

from typing import Any


EVENT_RULES = {
    "core_cpi": {"terms": ("core cpi", "core consumer price index"), "higher": "hawkish"},
    "cpi": {"terms": ("cpi", "consumer price index"), "higher": "hawkish"},
    "ppi": {"terms": ("ppi", "producer price index"), "higher": "hawkish"},
    "core_pce": {"terms": ("core pce", "core personal consumption expenditures"), "higher": "hawkish"},
    "pce": {"terms": ("pce", "personal consumption expenditures"), "higher": "hawkish"},
    "nfp": {"terms": ("nonfarm payroll", "employment situation", "jobs report", "payrolls"), "higher": "hawkish"},
    "unemployment": {"terms": ("unemployment rate", "jobless rate"), "higher": "dovish"},
    "retail_sales": {"terms": ("retail sales",), "higher": "hawkish"},
    "gdp": {"terms": ("gross domestic product", "gdp"), "higher": "hawkish"},
    "fomc": {"terms": ("fomc", "fed funds rate", "federal reserve rate decision", "interest rate decision"), "higher": "hawkish"},
}

def classify_event(name: str) -> str | None:
    text = (name or "").casefold()
    for event_type, rule in EVENT_RULES.items():
        if any(term in text for term in rule["terms"]):
            return event_type
    return None


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        # Accept common display forms such as "3.2%" and "250K".
        raw = str(value).strip().replace(",", "")
        multiplier = 1
        if raw.endswith("%"):
            raw = raw[:-1]
        elif raw[-1:].upper() == "K":
            raw, multiplier = raw[:-1], 1_000
        elif raw[-1:].upper() == "M":
            raw, multiplier = raw[:-1], 1_000_000
        return float(raw) * multiplier
    except (TypeError, ValueError):
        return None


def analyze_release(name: str, actual: Any = None, forecast: Any = None, previous: Any = None) -> dict:
    """Return a cautious macro read; missing consensus never becomes a guessed forecast."""
    event_type = classify_event(name)
    actual_n, forecast_n, previous_n = map(_number, (actual, forecast, previous))
    surprise = None if actual_n is None or forecast_n is None else round(actual_n - forecast_n, 6)
    surprise_label = "forecast_unavailable"
    macro_bias = "unknown"
    explanation = "Forecast konsensus tidak tersedia; jangan menyimpulkan kejutan data dari angka aktual saja."

    if actual_n is not None and forecast_n is not None and event_type:
        higher = EVENT_RULES[event_type]["higher"]
        if surprise == 0:
            surprise_label = "in_line"
            macro_bias = "mixed"
            explanation = "Hasil sesuai forecast; arah market belum terkonfirmasi."
        else:
            positive_surprise = surprise > 0
            if higher == "dovish":
                positive_surprise = not positive_surprise
            macro_bias = "hawkish" if positive_surprise else "dovish"
            surprise_label = "above_forecast" if actual_n > forecast_n else "below_forecast"
            explanation = (
                "Kejutan cenderung hawkish: dapat mendukung USD/yield dan menekan Gold/Nasdaq, "
                "tetapi tunggu konfirmasi harga."
                if macro_bias == "hawkish" else
                "Kejutan cenderung dovish: dapat melemahkan USD/yield dan mendukung Gold/Nasdaq, "
                "tetapi tunggu konfirmasi harga."
            )

    return {
        "event_type": event_type,
        "event_name": (str(name).strip() if name and str(name).strip() else None),
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
        "actual_numeric": actual_n,
        "forecast_numeric": forecast_n,
        "previous_numeric": previous_n,
        "surprise": surprise,
        "surprise_label": surprise_label,
        "macro_bias": macro_bias,
        "market_confirmation": "not_checked",
        "explanation": explanation,
        "source_note": "Gunakan hanya nilai dari sumber publik terverifikasi; forecast yang kosong tidak diestimasi.",
    }
