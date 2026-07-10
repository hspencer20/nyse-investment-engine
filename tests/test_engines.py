from technical_engine import technical_score
from risk_engine import risk_score


def test_technical_score_range():
    metrics = {
        "last": 100, "sma20": 105, "sma50": 100, "sma200": 90,
        "ema20": 103, "ema50": 98, "macd": 2, "macd_signal": 1,
        "rsi14": 58, "ret_1m": 0.05, "ret_3m": 0.15,
        "ret_6m": 0.20, "relative_volume": 1.2,
    }
    score = technical_score(metrics)["technical_score"]
    assert 0 <= score <= 100


def test_risk_score_range():
    metrics = {"volatility": 0.30, "max_drawdown_1y": -0.20}
    fundamentals = {"beta": 1.2, "debt_to_equity": 80}
    score = risk_score(metrics, fundamentals)["risk_score"]
    assert 10 <= score <= 90
