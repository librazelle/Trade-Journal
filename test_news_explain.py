from app.services.news_explain import explain_news


def test_fomc_has_normal_and_beginner_indonesian_explanations():
    result = explain_news("Federal Reserve announces FOMC rate decision", "Interest rate decision")
    assert "bank sentral AS" in result["summary_id"]
    assert "Intinya" in result["summary_simple"]
    assert "BUY/SELL" not in result["summary_simple"]


def test_unknown_news_does_not_invent_specific_market_claims():
    result = explain_news("Community art event", "Local program announcement")
    assert "belum bisa diringkas secara spesifik" in result["summary_id"]
    assert "Buka berita aslinya" in result["summary_simple"]
