from __future__ import annotations

from config import MIN_ACTIONABLE_RR


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def score_stock(metrics: dict[str, float | str]) -> dict[str, float | str | bool]:
    last = float(metrics["last"])

    trend = 0.0
    trend += 12 if last > float(metrics["sma20"]) else -12
    trend += 15 if float(metrics["sma20"]) > float(metrics["sma50"]) else -15
    trend += 18 if float(metrics["sma50"]) > float(metrics["sma200"]) else -18

    momentum = (
        clamp(float(metrics["ret_1m"]) * 100, -15, 15)
        + clamp(float(metrics["ret_3m"]) * 45, -18, 18)
        + clamp(float(metrics["ret_6m"]) * 25, -15, 15)
        + (8 if float(metrics["macd"]) > float(metrics["macd_signal"]) else -8)
    )

    rsi14 = float(metrics["rsi14"])
    if 45 <= rsi14 <= 68:
        rsi_adjustment = 8
    elif rsi14 > 78:
        rsi_adjustment = -10
    elif rsi14 < 30:
        rsi_adjustment = 4
    else:
        rsi_adjustment = 0

    risk_penalty = clamp(float(metrics["volatility"]) * 18, 0, 18)
    raw_score = 50 + trend * 0.55 + momentum * 0.65 + rsi_adjustment - risk_penalty
    quant_score = round(clamp(raw_score, 0, 100), 1)

    expected_return = clamp((quant_score - 50) / 220, -0.18, 0.18)
    probability_up = round(clamp(50 + (quant_score - 50) * 0.62, 25, 82), 1)
    probability_down = round(100 - probability_up, 1)
    direction = "long" if expected_return >= 0 else "short"

    atr_pct = float(metrics["atr"]) / last if last else 0.05

    # The operational Take Profit remains inside the 3-month Target.
    take_pct_abs = clamp(abs(expected_return) * 0.78, 0.01, 0.15)

    # Technical risk reference. It is not artificially tightened to force a 2:1 setup.
    stop_pct_abs = clamp(max(atr_pct * 1.6, 0.02), 0.02, 0.09)

    risk_reward = take_pct_abs / stop_pct_abs if stop_pct_abs else 0.0
    actionable = risk_reward >= MIN_ACTIONABLE_RR

    target = last * (1 + expected_return)

    if direction == "long":
        stop = last * (1 - stop_pct_abs)
        take = last * (1 + take_pct_abs)
        stop_pct = -stop_pct_abs
        take_pct = take_pct_abs

        if quant_score >= 82 and actionable:
            signal, confidence = "Strong Buy", "High"
            position_status, action = "Increase", "Accumulate in stages."
        elif quant_score >= 68 and actionable:
            signal, confidence = "Buy", "Medium-High"
            position_status, action = "Accumulate", "Add on pullbacks."
        elif quant_score >= 55:
            signal, confidence = "Hold / Watch", "Medium"
            position_status, action = "Maintain", "Maintain; await a stronger entry."
        else:
            signal, confidence = "Hold", "Medium"
            position_status, action = "Maintain", "Maintain existing exposure."
    else:
        stop = last * (1 + stop_pct_abs)
        take = last * (1 - take_pct_abs)
        stop_pct = stop_pct_abs
        take_pct = -take_pct_abs

        if quant_score <= 18 and actionable:
            signal, confidence = "Strong Sell", "High"
            position_status, action = "Exit / Short", "Reduce or short only within risk limits."
        elif quant_score <= 30 and actionable:
            signal, confidence = "Sell", "Medium-High"
            position_status, action = "Reduce", "Reduce exposure."
        elif quant_score < 45:
            signal, confidence = "Watch / Avoid New Position", "Medium"
            position_status, action = "Watch", "Do not initiate a new position."
        else:
            signal, confidence = "Hold", "Medium"
            position_status, action = "Maintain", "Maintain existing exposure."

    return {
        "quant_score": quant_score,
        "expected_return": round(expected_return, 6),
        "probability_up": probability_up,
        "probability_down": probability_down,
        "direction": direction,
        "target": round(target, 4),
        "stop": round(stop, 4),
        "stop_pct": round(stop_pct, 6),
        "take": round(take, 4),
        "take_pct": round(take_pct, 6),
        "risk_reward": round(risk_reward, 2),
        "actionable": actionable,
        "signal": signal,
        "confidence": confidence,
        "position_status": position_status,
        "action": action,
    }
