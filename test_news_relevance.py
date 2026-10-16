from app.services.news_relevance import high_impact_news, relevance_for_news


def test_fomc_news_maps_to_gold_and_us_indices():
    result = relevance_for_news(
        "Federal Reserve announces FOMC rate decision",
        "Federal funds target range",
        92,
    )
    assert result is not None
    assert result["event_type"] == "FOMC / kebijakan Fed"
    assert "XAUUSD" in result["instruments"]
    assert "NASDAQ100" in result["instruments"]
    assert "S&P500" in result["instruments"]


def test_high_impact_news_ranks_official_macro_story_first():
    items = [
        {"title": "Local community announcement", "summary": "", "impact": 30, "tier": 2,
         "source": "Local", "published_at": "2026-10-16T10:00:00Z"},
        {"title": "Consumer Price Index CPI release", "summary": "Inflation data", "impact": 80, "tier": 1,
         "source": "BLS", "published_at": "2026-10-16T12:00:00Z"},
    ]
    result = high_impact_news(items)
    assert len(result) == 1
    assert result[0]["source"] == "BLS"
    assert "XAUUSD" in result[0]["instruments"]


def test_unrelated_news_is_not_misclassified():
    assert relevance_for_news("Community event schedule", "Local announcements", 50) is None
