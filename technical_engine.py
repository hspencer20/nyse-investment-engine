from __future__ import annotations


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def technical_score(metrics: dict) -> dict:
    last = float(metrics["last"])
    score = 50.0

    score += 8 if last > metrics["sma20"] else -8
    score += 10 if metrics["sma20"] > metrics["sma50"] else -10
    score += 12 if metrics["sma50"] > metrics["sma200"] else -12
    score += 5 if metrics["ema20"] > metrics["ema50"] else -5
    score += 7 if metrics["macd"] > metrics["macd_signal"] else -7

    rsi14 = float(metrics["rsi14"])
    if 45 <= rsi14 <= 68:
        score += 7
    elif rsi14 > 78:
        score -= 8
    elif rsi14 < 30:
        score += 3

    score += clamp(float(metrics["ret_1m"]) * 55, -10, 10)
    score += clamp(float(metrics["ret_3m"]) * 30, -12, 12)
    score += clamp(float(metrics["ret_6m"]) * 18, -10, 10)
    score += clamp((float(metrics["relative_volume"]) - 1) * 8, -5, 5)

    return {
        "technical_score": round(clamp(score, 0, 100), 1),
        "technical_trend": "Bullish" if score >= 60 else "Bearish" if score <= 40 else "Neutral",
    }
