from decision_engine import finalize_decision


def components():
    technical = {"technical_score": 80}
    fundamental = {
        "fundamental_score": 75,
        "fundamental_strengths": ["Revenue Growth"],
        "fundamental_risks": [],
    }
    events = {
        "event_score": 70,
        "recent_catalyst": "Major contract announced.",
        "recent_risk": "No material recent risk identified.",
    }
    analyst = {
        "analyst_score": 72,
        "analyst_target_mean": 120,
    }
    risk = {"risk_score": 70}
    metrics = {"last": 100, "atr": 2.5}
    return technical, fundamental, events, analyst, risk, metrics


def test_long_decision_levels():
    result = finalize_decision(*components())
    assert result["direction"] == "long"
    assert result["stop"] < 100
    assert result["take"] > 100
    assert result["take"] < result["target"]


def test_rr_filter_blocks_low_quality_trade():
    technical, fundamental, events, analyst, risk, metrics = components()
    metrics["atr"] = 9
    result = finalize_decision(technical, fundamental, events, analyst, risk, metrics)
    if result["risk_reward"] < 2:
        assert result["recommendation"] not in {"Strong Buy", "Buy", "Strong Sell", "Sell"}
