from model import score_stock


def base_metrics():
    return {
        "last": 100.0,
        "sma20": 105.0,
        "sma50": 100.0,
        "sma200": 90.0,
        "rsi14": 58.0,
        "macd": 2.0,
        "macd_signal": 1.0,
        "atr": 3.0,
        "avg_volume": 1_000_000.0,
        "ret_1m": 0.08,
        "ret_3m": 0.20,
        "ret_6m": 0.30,
        "volatility": 0.25,
    }


def test_long_stop_below_and_take_below_target():
    result = score_stock(base_metrics())
    assert result["direction"] == "long"
    assert result["stop"] < 100
    assert result["take"] > 100
    assert result["take"] < result["target"]


def test_short_stop_above_and_take_above_target():
    metrics = base_metrics()
    metrics.update(
        {
            "sma20": 90.0,
            "sma50": 95.0,
            "sma200": 110.0,
            "rsi14": 35.0,
            "macd": -2.0,
            "macd_signal": -1.0,
            "ret_1m": -0.10,
            "ret_3m": -0.25,
            "ret_6m": -0.35,
            "volatility": 0.30,
        }
    )
    result = score_stock(metrics)
    assert result["direction"] == "short"
    assert result["stop"] > 100
    assert result["take"] < 100
    assert result["take"] > result["target"]


def test_non_actionable_trade_not_labeled_buy_or_sell():
    metrics = base_metrics()
    metrics["atr"] = 8.0
    result = score_stock(metrics)
    if result["risk_reward"] < 2:
        assert result["signal"] not in {"Strong Buy", "Buy", "Strong Sell", "Sell"}
