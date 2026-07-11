from __future__ import annotations

from config import MIN_ACTIONABLE_RR, WATCHLIST


def validate_payload(payload: dict) -> None:
    if payload.get("version") != "2.0.2":
        raise ValueError("Unexpected report version")
    if payload.get("report_type") not in {"PRE_MARKET", "POST_MARKET"}:
        raise ValueError("Invalid report type")
    if len(payload.get("long_top_20", [])) != 20:
        raise ValueError("Long ranking must contain 20 entries")
    if len(payload.get("short_top_20", [])) != 20:
        raise ValueError("Short ranking must contain 20 entries")

    watchlist = {item["ticker"] for item in payload.get("strategic_watchlist", [])}
    if watchlist != set(WATCHLIST):
        raise ValueError("Strategic Watchlist is incomplete")

    required = {
        "ticker", "company", "sector", "last", "target_3m", "change_dollar",
        "change_percent", "confidence", "combined_score", "stop_loss",
        "stop_loss_percent", "take_profit", "take_profit_percent",
        "risk_reward", "recommendation", "position_status", "action",
        "recent_catalyst", "recent_risk",
    }

    for section in ("highest_conviction_longs", "highest_conviction_shorts", "strategic_watchlist"):
        for item in payload.get(section, []):
            missing = required.difference(item)
            if missing:
                raise ValueError(f"Missing fields for {item.get('ticker')}: {sorted(missing)}")
            if item["recommendation"] in {"Strong Buy", "Buy", "Strong Sell", "Sell"}:
                if item["risk_reward"] < MIN_ACTIONABLE_RR:
                    raise ValueError(f"Actionable signal below minimum R/R for {item['ticker']}")
            if item["target_3m"] == item["take_profit"]:
                raise ValueError(f"Target and Take Profit must differ for {item['ticker']}")
