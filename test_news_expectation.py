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


def test_core_cpi_keeps_specific_event_type_and_label():
    result = analyze_release('Core CPI', actual='3.1%', forecast='3.3%')
    assert result['event_type'] == 'core_cpi'
    assert result['event_name'] == 'Core CPI'
    assert result['macro_bias'] == 'dovish'


def test_blank_input_does_not_create_a_surprise():
    result = analyze_release('Core CPI', actual='', forecast='', previous='')
    assert result['event_name'] == 'Core CPI'
    assert result['surprise'] is None
    assert result['macro_bias'] == 'unknown'


def test_unknown_event_is_not_given_macro_bias():
    result = analyze_release('Mystery indicator', actual='5', forecast='1')
    assert result['event_type'] is None
    assert result['macro_bias'] == 'unknown'
