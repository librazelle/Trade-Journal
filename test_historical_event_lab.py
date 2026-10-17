from app.services.historical_event_lab import summarize_reactions


def test_summary_computes_percent_change_and_sample_warning():
    rows = [
        {"event_type": "CPI", "instrument": "XAUUSD", "expected_direction": "up", "price_before": 2000, "price_after_15m": 2020},
        {"event_type": "CPI", "instrument": "XAUUSD", "expected_direction": "down", "price_before": 2000, "price_after_15m": 1980},
        {"event_type": "CPI", "instrument": "XAUUSD", "expected_direction": "up", "price_before": 2000, "price_after_15m": 2000},
    ]
    result = summarize_reactions(rows)[0]
    assert result["samples"] == 3
    assert result["median_change_pct"] == 0.0
    assert result["positive_samples"] == 1
    assert result["negative_samples"] == 1
    assert result["flat_samples"] == 1
    assert result["bias_scored_samples"] == 2
    assert result["sample_warning"].startswith("Sampel sangat kecil")


def test_summary_ignores_invalid_rows_and_groups_instrument():
    rows = [
        {"event_type": "NFP", "instrument": "nasdaq100", "expected_direction": "up", "price_before": 100, "price_after_15m": 101},
        {"event_type": "NFP", "instrument": "NASDAQ100", "expected_direction": "down", "price_before": 0, "price_after_15m": 101},
        {"event_type": "", "instrument": "XAUUSD", "expected_direction": "up", "price_before": 100, "price_after_15m": 101},
        {"event_type": "NFP", "instrument": "NASDAQ100", "expected_direction": "down", "price_before": 100, "price_after_15m": 99},
    ]
    result = summarize_reactions(rows)
    assert len(result) == 1
    assert result[0]["instrument"] == "NASDAQ100"
    assert result[0]["samples"] == 2
    assert result[0]["bias_aligned_pct"] == 100.0


def test_empty_dataset_returns_empty_list():
    assert summarize_reactions([]) == []


def test_summary_ignores_nan_and_infinite_prices():
    rows = [
        {"event_type": "CPI", "instrument": "XAUUSD", "expected_direction": "up", "price_before": float("nan"), "price_after_15m": 2010},
        {"event_type": "CPI", "instrument": "XAUUSD", "expected_direction": "up", "price_before": 2000, "price_after_15m": float("inf")},
        {"event_type": "CPI", "instrument": "XAUUSD", "expected_direction": "up", "price_before": 2000, "price_after_15m": 2010},
    ]
    result = summarize_reactions(rows)
    assert len(result) == 1
    assert result[0]["samples"] == 1
    assert result[0]["median_change_pct"] == 0.5
