from app.services.news_expectation import analyze_release, classify_event


def test_cpi_below_forecast_is_dovish():
    result = analyze_release('CPI', actual='3.1%', forecast='3.3%')
    assert result['surprise'] == -0.2
    assert result['macro_bias'] == 'dovish'


def test_missing_forecast_is_not_guessed():
    result = analyze_release('CPI', actual='3.1%')
    assert result['surprise'] is None
    assert result['macro_bias'] == 'unknown'


def test_event_classification():
    assert classify_event('Nonfarm Payrolls') == 'nfp'
    assert classify_event('FOMC rate decision') == 'fomc'
