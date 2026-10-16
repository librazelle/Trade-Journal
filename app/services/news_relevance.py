"""Rule-based news-to-market relevance hints; not a measured correlation coefficient."""

RULES = [
    (("fomc", "federal reserve", "fed funds rate", "rate decision", "interest rate decision", "powell"),
     "FOMC / kebijakan Fed", ["XAUUSD", "NASDAQ100", "S&P500", "DXY", "US10Y"]),
    (("consumer price index", "cpi", "producer price index", "ppi", "personal consumption expenditures", "pce", "inflation"),
     "Inflasi AS", ["XAUUSD", "NASDAQ100", "S&P500", "DXY", "US10Y"]),
    (("nonfarm payroll", "employment situation", "unemployment rate", "payroll employment", "jobs report"),
     "Data tenaga kerja AS", ["XAUUSD", "NASDAQ100", "S&P500", "DXY", "US10Y"]),
    (("gross domestic product", "gdp", "economic growth"),
     "Pertumbuhan ekonomi AS", ["NASDAQ100", "S&P500", "XAUUSD", "DXY", "US10Y"]),
    (("treasury", "bond yield", "yield", "auction"),
     "Obligasi / yield AS", ["XAUUSD", "NASDAQ100", "S&P500", "DXY"]),
    (("tariff", "trade war", "sanction", "geopolitical", "war", "missile"),
     "Risiko geopolitik / perdagangan", ["XAUUSD", "USOIL", "S&P500", "NASDAQ100"]),
]


def relevance_for_news(title: str, summary: str = "", impact: int = 0) -> dict | None:
    text = f"{title or ''} {summary or ''}".lower()
    for keywords, event_type, instruments in RULES:
        if any(keyword in text for keyword in keywords):
            return {
                "event_type": event_type,
                "instruments": instruments,
                "impact": int(impact or 0),
                "title": title,
            }
    return None


def high_impact_news(items: list[dict], limit: int = 5) -> list[dict]:
    """Return the strongest known macro headlines with transparent relevance labels."""
    ranked = []
    seen = set()
    for item in items:
        relevance = relevance_for_news(
            item.get("title", ""), item.get("summary", ""), item.get("impact", 0)
        )
        if not relevance:
            continue
        # Prefer high impact score and official source tier. This is a heuristic,
        # not a statistical correlation or a forecast of price direction.
        score = int(item.get("impact", 0) or 0) + (10 if int(item.get("tier", 3) or 3) == 1 else 0)
        key = (item.get("title", "").strip().lower(), item.get("source", "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        ranked.append({**item, **relevance, "ranking_score": score})
    return sorted(ranked, key=lambda item: (item["ranking_score"], item.get("published_at", "")), reverse=True)[:limit]
