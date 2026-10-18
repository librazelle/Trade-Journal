from app.services.trade_validator import validate_setup


def base(**overrides):
    values = dict(
        instrument="XAUUSD", direction="long", entry="2650", stop_loss="2645",
        take_profit="2660", risk_pct="0.5", max_risk_pct="1",
        htf_bias="bullish", setup="M5 FVG + M1 BOS",
        trigger_confirmed="yes", liquidity_checked="yes", news_checked="yes",
        rr_min="1.5",
    )
    values.update(overrides)
    return values


def test_complete_checklist_ready_but_no_win_probability():
    result = validate_setup(**base())
    assert result["status"] == "READY FOR YOUR DECISION"
    assert result["risk_reward"] == 2.0
    assert result["win_probability"] is None


def test_missing_stop_loss_blocks():
    result = validate_setup(**base(stop_loss=""))
    assert result["status"] == "BLOCKED"
    assert any("Stop-loss" in item for item in result["blockers"])


def test_risk_above_user_limit_blocks():
    result = validate_setup(**base(risk_pct="1.5", max_risk_pct="1"))
    assert result["status"] == "BLOCKED"


def test_wrong_long_geometry_blocks():
    result = validate_setup(**base(stop_loss="2660", take_profit="2640"))
    assert result["status"] == "BLOCKED"


def test_missing_trigger_requires_review():
    result = validate_setup(**base(trigger_confirmed="no"))
    assert result["status"] == "REVIEW REQUIRED"


def test_conflicting_htf_bias_requires_review():
    result = validate_setup(**base(htf_bias="bearish"))
    assert result["status"] == "REVIEW REQUIRED"


def test_invalid_minimum_rr_blocks():
    result = validate_setup(**base(rr_min="not-a-number"))
    assert result["status"] == "BLOCKED"
    assert any("Minimum R:R" in item for item in result["blockers"])


def test_zero_minimum_rr_blocks():
    result = validate_setup(**base(rr_min="0"))
    assert result["status"] == "BLOCKED"
