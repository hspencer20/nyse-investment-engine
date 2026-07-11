from report import _rank_changes

def item(ticker):
    return {
        "ticker": ticker,
        "direction": "long",
        "recommendation": "Buy",
        "target_3m": 110,
        "probability_up": 60,
        "probability_down": 40,
        "stop_loss": 95,
        "take_profit": 108,
        "risk_reward": 2.5,
    }

def test_rank_changes():
    result = _rank_changes(
        [item("AAPL"), item("MSFT")],
        [item("MSFT"), item("NVDA")],
    )
    by_ticker = {x["ticker"]: x for x in result}
    assert by_ticker["AAPL"]["status"] == "NEW"
    assert by_ticker["MSFT"]["status"] == "MOVED"
    assert by_ticker["NVDA"]["status"] == "EXITED"
