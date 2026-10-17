from app.services.news_relevance import is_market_relevant_news, relevance_for_news


def test_macro_and_market_headlines_are_relevant():
    assert is_market_relevant_news({"title": "US inflation rises more than expected", "source": "BBC News · Economics"})
    assert is_market_relevant_news({"title": "Federal Reserve signals interest rate decision", "source": "Federal Reserve"})
    assert is_market_relevant_news({"title": "Nasdaq futures fall as chip stocks slide", "source": "BBC News · Business"})


def test_unrelated_headlines_are_filtered():
    assert not is_market_relevant_news({"title": "Celebrity announces new television show", "summary": "Fans react online", "source": "BBC News · World"})
    assert not is_market_relevant_news({"title": "Local football club wins weekend match", "source": "The Guardian · World"})


def test_bbc_economics_feed_accepts_broader_economic_policy_topics():
    assert is_market_relevant_news({"title": "Why the cost of living is changing", "source": "BBC News · Economics"})


def test_relevance_mapping_has_instrument_context():
    result = relevance_for_news("US inflation jumps", impact=72)
    assert result is not None
    assert "XAUUSD" in result["instruments"]
    assert result["impact"] == 72
