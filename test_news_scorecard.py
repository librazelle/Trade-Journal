from app.services.news_scorecard import build_news_scorecard


def test_macro_headline_marks_relevant_assets_without_predicting_direction():
    card = build_news_scorecard(
        title="Federal Reserve signals interest rate decision",
        summary="Officials discuss inflation and treasury yields.",
        source="Federal Reserve",
        tier=1,
    )
    assert card["event_type"] == "Kebijakan moneter"
    assert card["relevance"]["XAUUSD"]["relevance"] in ("Tinggi", "Sedang")
    assert card["relevance"]["NASDAQ100"]["relevance"] in ("Tinggi", "Sedang")
    assert card["direction"] == "Belum ditentukan"
    assert "bukan model statistik" in card["method"]


def test_unrelated_headline_does_not_claim_clear_market_relevance():
    card = build_news_scorecard(
        title="Local museum opens a new photography exhibit",
        summary="The exhibit opens this weekend.",
        source="Local Culture Desk",
        tier=3,
    )
    assert card["event_type"] == "Belum terklasifikasi"
    assert all(
        item["relevance"] == "Rendah / belum jelas"
        for item in card["relevance"].values()
    )
    assert card["evidence_quality"] == "Rendah–sedang"


def test_scorecard_handles_missing_metadata_safely():
    card = build_news_scorecard("", "", "", None)
    assert set(card["relevance"]) == {"XAUUSD", "NASDAQ100", "DXY"}
    assert card["direction"] == "Belum ditentukan"
    assert isinstance(card["evidence_note"], str)
