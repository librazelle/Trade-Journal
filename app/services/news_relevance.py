"""Rule-based market relevance filtering and macro headline ranking.

These are transparent keyword heuristics, not measured correlations or trade signals.
"""

RULES = [
    (("fomc", "federal reserve", "fed funds rate", "rate decision", "interest rate decision", "interest rates", "powell", "central bank", "monetary policy"),
     "Kebijakan bank sentral", ["XAUUSD", "NASDAQ100", "S&P500", "DXY", "US10Y"]),
    (("consumer price index", "cpi", "producer price index", "ppi", "personal consumption expenditures", "pce", "inflation", "inflationary"),
     "Inflasi", ["XAUUSD", "NASDAQ100", "S&P500", "DXY", "US10Y"]),
    (("nonfarm payroll", "employment situation", "unemployment rate", "payroll employment", "jobs report", "jobless claims", "labour market", "labor market", "wage growth"),
     "Data tenaga kerja", ["XAUUSD", "NASDAQ100", "S&P500", "DXY", "US10Y"]),
    (("gross domestic product", " gdp", "economic indicators", "economic data", "economic report", "economic growth", "economic slowdown", "recession", "economic outlook", "retail sales", "consumer spending", "personal income", "manufacturing activity", "pmi", "ism"),
     "Pertumbuhan ekonomi", ["NASDAQ100", "S&P500", "XAUUSD", "DXY", "US10Y"]),
    (("treasury", "bond yield", "bond yields", "government bond", "government bonds", "10-year yield", "10 year yield", "yield curve", "bond auction"),
     "Obligasi / yield", ["XAUUSD", "NASDAQ100", "S&P500", "DXY", "US10Y"]),
    (("tariff", "tariffs", "trade war", "trade deal", "trade talks", "sanction", "sanctions", "geopolitical", "missile", "military strike", "ceasefire", "oil prices", "crude oil", "opec"),
     "Risiko geopolitik / perdagangan / energi", ["XAUUSD", "USOIL", "S&P500", "NASDAQ100", "DXY"]),
    (("stock market", "stock markets", "share prices", "equity market", "equity markets", "nasdaq", "s&p 500", "dow jones", "wall street", "market sell-off", "market rally", "market volatility", "market futures"),
     "Pasar saham", ["NASDAQ100", "S&P500", "US30"]),
    (("dollar index", "us dollar", "dollar strengthens", "dollar weakens", "forex market", "currency market", "exchange rate", "yen", "euro"),
     "Valuta asing", ["DXY", "XAUUSD", "EURUSD", "USDJPY"]),
    (("bitcoin", "crypto market", "cryptocurrency", "digital assets"),
     "Aset kripto", ["BTCUSD"]),
    (("semiconductor", "chip stocks", "nvidia", "apple shares", "technology stocks", "tech stocks", "big tech earnings"),
     "Saham teknologi", ["NASDAQ100", "S&P500"]),
]

BBC_ECONOMICS_TERMS = (
    "economy", "economic", "inflation", "interest rate", "central bank", "jobs",
    "employment", "growth", "recession", "market", "business", "trade", "tax",
    "budget", "wages", "prices", "cost of living", "bank", "investment", "shares",
    "stocks", "currency", "dollar", "oil", "energy", "tariff", "debt", "gdp",
)


def relevance_for_news(title: str, summary: str = "", impact: int = 0) -> dict | None:
    text = f" {title or ''} {summary or ''} ".lower()
    for keywords, event_type, instruments in RULES:
        if any(keyword in text for keyword in keywords):
            return {
                "event_type": event_type,
                "instruments": instruments,
                "impact": int(impact or 0),
                "title": title,
            }
    return None


def is_market_relevant_news(item: dict) -> bool:
    """Keep macro, market, monetary-policy, and instrument-related headlines in the trading feed."""
    title = item.get("title", "") or ""
    summary = item.get("summary", "") or ""
    source = (item.get("source", "") or "").lower()
    if relevance_for_news(title, summary, item.get("impact", 0)):
        return True

    # BBC's dedicated Economics feed can cover broader economic policy stories that
    # do not always mention a specific instrument or release acronym in the headline.
    if "bbc" in source and "econom" in source:
        text = f"{title} {summary}".lower()
        return any(term in text for term in BBC_ECONOMICS_TERMS)
    return False


def high_impact_news(items: list[dict], limit: int = 5) -> list[dict]:
    """Return the strongest known macro headlines with transparent relevance labels."""
    ranked = []
    seen = set()
    for item in items:
        searchable_summary = " ".join(
            part for part in [
                item.get("summary", ""),
                " ".join(item.get("tags_list", []) or []),
                item.get("tags", "").replace(",", " ") if isinstance(item.get("tags", ""), str) else "",
            ] if part
        )
        if "major economic indicators latest numbers" in item.get("title", "").lower():
            relevance = {
                "event_type": "Indikator makro AS (CPI, tenaga kerja, PPI)",
                "instruments": ["XAUUSD", "NASDAQ100", "S&P500", "DXY", "US10Y"],
                "impact": int(item.get("impact", 0) or 0),
                "title": item.get("title", ""),
            }
        else:
            relevance = relevance_for_news(
                item.get("title", ""), searchable_summary, item.get("impact", 0)
            )
        if not relevance:
            continue
        score = int(item.get("impact", 0) or 0) + (10 if int(item.get("tier", 3) or 3) == 1 else 0)
        key = (item.get("title", "").strip().lower(), item.get("source", "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        ranked.append({**item, **relevance, "ranking_score": score})
    return sorted(ranked, key=lambda item: (item["ranking_score"], item.get("published_at", "")), reverse=True)[:limit]
