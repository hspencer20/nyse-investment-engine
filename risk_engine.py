from __future__ import annotations


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def risk_score(metrics: dict, fundamentals: dict) -> dict:
    volatility = float(metrics["volatility"])
    drawdown = abs(float(metrics["max_drawdown_1y"]))
    beta = fundamentals.get("beta")
    beta = float(beta) if beta is not None else 1.0

    score = 75.0
    score -= clamp(volatility * 35, 0, 25)
    score -= clamp(drawdown * 35, 0, 20)
    score -= clamp(abs(beta - 1.0) * 10, 0, 10)

    debt = fundamentals.get("debt_to_equity")
    if debt is not None:
        normalized = float(debt) / 100 if float(debt) > 10 else float(debt)
        score -= clamp(max(normalized - 1.5, 0) * 4, 0, 10)

    return {
        "risk_score": round(clamp(score, 10, 90), 1),
        "risk_level": "Low" if score >= 70 else "High" if score <= 40 else "Medium",
    }
