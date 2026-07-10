from decision_engine import finalize_decision


def test_conflict_reduces_conviction():
    quant = {"quant_score": 80, "target": 115, "stop": 95, "stop_pct": -0.05}
    thesis = {"thesis_score": 30, "analyst_target_mean": None}
    result = finalize_decision(quant, thesis, 100)
    assert result["signal_conflict"] is True
    assert result["recommendation"] == "Hold / Watch"


def test_rr_filter_blocks_actionable_signal():
    quant = {"quant_score": 85, "target": 110, "stop": 91, "stop_pct": -0.09}
    thesis = {"thesis_score": 80, "analyst_target_mean": None}
    result = finalize_decision(quant, thesis, 100)
    assert result["risk_reward"] < 2
    assert result["recommendation"] not in {"Strong Buy", "Buy", "Strong Sell", "Sell"}
