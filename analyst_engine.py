from __future__ import annotations

from typing import Any


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def analyst_score(stock, last_price: float) -> dict:
    score = 50.0
    mean_target = None
    recommendation_balance = None
    recommendation_text = "Analyst data unavailable."

    try:
        targets = stock.get_analyst_price_targets() or {}
        mean_target = targets.get("mean") or targets.get("current")
    except Exception:
        mean_target = None

    if mean_target:
        upside = float(mean_target) / last_price - 1
        score += clamp(upside * 80, -20, 20)
        recommendation_text = f"Analyst mean target implies {upside * 100:+.1f}%."

    try:
        summary = stock.get_recommendations_summary()
    except Exception:
        summary = None

    if summary is not None and hasattr(summary, "empty") and not summary.empty:
        row = summary.iloc[0].to_dict()
        sb = float(row.get("strongBuy", 0) or 0)
        b = float(row.get("buy", 0) or 0)
        h = float(row.get("hold", 0) or 0)
        s = float(row.get("sell", 0) or 0)
        ss = float(row.get("strongSell", 0) or 0)
        total = sb + b + h + s + ss
        if total:
            recommendation_balance = (2 * sb + b - s - 2 * ss) / total
            score += clamp(recommendation_balance * 18, -15, 15)

    return {
        "analyst_score": round(clamp(score, 15, 85), 1),
        "analyst_target_mean": round(float(mean_target), 4) if mean_target else None,
        "analyst_recommendation_balance": recommendation_balance,
        "analyst_note": recommendation_text,
    }
