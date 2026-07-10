def clamp(value, low, high):
    return max(low, min(high, value))

def score_stock(m):
    trend = 0
    trend += 12 if m["last"] > m["sma20"] else -12
    trend += 15 if m["sma20"] > m["sma50"] else -15
    trend += 18 if m["sma50"] > m["sma200"] else -18

    momentum = (
        clamp(m["ret_1m"] * 100, -15, 15)
        + clamp(m["ret_3m"] * 45, -18, 18)
        + clamp(m["ret_6m"] * 25, -15, 15)
        + (8 if m["macd"] > m["macd_signal"] else -8)
    )

    rsi_adj = 8 if 45 <= m["rsi14"] <= 68 else (-10 if m["rsi14"] > 78 else 0)
    risk_penalty = clamp(m["volatility"] * 18, 0, 18)
    score = round(clamp(50 + trend * 0.55 + momentum * 0.65 + rsi_adj - risk_penalty, 0, 100), 1)

    expected_return = clamp((score - 50) / 220, -0.18, 0.18)
    probability_up = round(clamp(50 + (score - 50) * 0.62, 25, 82), 1)
    probability_down = round(100 - probability_up, 1)

    atr_pct = m["atr"] / m["last"] if m["last"] else 0.05
    stop_pct = clamp(max(atr_pct * 1.6, 0.045), 0.045, 0.09)
    take_pct = clamp(max(abs(expected_return) * 0.78, 0.045), 0.045, 0.15)

    if score >= 82:
        signal, confidence = "Strong Buy", "High"
    elif score >= 68:
        signal, confidence = "Buy", "Medium-High"
    elif score >= 55:
        signal, confidence = "Hold / Buy", "Medium"
    elif score >= 45:
        signal, confidence = "Hold", "Medium"
    elif score >= 30:
        signal, confidence = "Reduce", "Medium"
    else:
        signal, confidence = "Sell", "High"

    return {
        "quant_score": score,
        "expected_return": expected_return,
        "probability_up": probability_up,
        "probability_down": probability_down,
        "target": m["last"] * (1 + expected_return),
        "stop": m["last"] * (1 - stop_pct),
        "stop_pct": -stop_pct,
        "take": m["last"] * (1 + take_pct if expected_return >= 0 else 1 - take_pct),
        "take_pct": take_pct if expected_return >= 0 else -take_pct,
        "risk_reward": take_pct / stop_pct,
        "signal": signal,
        "confidence": confidence,
    }
