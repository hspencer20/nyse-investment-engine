from __future__ import annotations

from config import MIN_ACTIONABLE_RR, QUANT_WEIGHT, THESIS_WEIGHT


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def finalize_decision(quant: dict, thesis: dict, last_price: float) -> dict:
    quant_score = float(quant["quant_score"])
    thesis_score = float(thesis["thesis_score"])
    combined_score = round(quant_score * QUANT_WEIGHT + thesis_score * THESIS_WEIGHT, 1)
    analyst_target = thesis.get("analyst_target_mean")
    quant_target = float(quant["target"])
    blended_target = quant_target * 0.65 + float(analyst_target) * 0.35 if analyst_target else quant_target
    expected_return = clamp(blended_target / last_price - 1, -0.20, 0.20)
    direction = "long" if expected_return >= 0 else "short"
    stop = float(quant["stop"])
    stop_pct = float(quant["stop_pct"])
    take_pct_abs = max(min(abs(expected_return) * 0.75, 0.15), 0.01)
    if direction == "long":
        take = last_price * (1 + take_pct_abs)
        take_pct = take_pct_abs
    else:
        take = last_price * (1 - take_pct_abs)
        take_pct = -take_pct_abs
    risk_pct_abs = abs(stop_pct)
    risk_reward = take_pct_abs / risk_pct_abs if risk_pct_abs else 0.0
    actionable = risk_reward >= MIN_ACTIONABLE_RR
    if direction == "long":
        if combined_score >= 82 and actionable:
            recommendation, confidence, status, action = "Strong Buy", "High", "Increase", "Accumulate in stages."
        elif combined_score >= 68 and actionable:
            recommendation, confidence, status, action = "Buy", "Medium-High", "Accumulate", "Add on pullbacks."
        elif combined_score >= 55:
            recommendation, confidence, status, action = "Hold / Watch", "Medium", "Maintain", "Maintain; await a stronger entry."
        else:
            recommendation, confidence, status, action = "Hold", "Medium", "Maintain", "Maintain existing exposure."
    else:
        if combined_score <= 18 and actionable:
            recommendation, confidence, status, action = "Strong Sell", "High", "Exit / Short", "Reduce or short only within risk limits."
        elif combined_score <= 30 and actionable:
            recommendation, confidence, status, action = "Sell", "Medium-High", "Reduce", "Reduce exposure."
        elif combined_score < 45:
            recommendation, confidence, status, action = "Watch / Avoid New Position", "Medium", "Watch", "Do not initiate a new position."
        else:
            recommendation, confidence, status, action = "Hold", "Medium", "Maintain", "Maintain existing exposure."
    conflict = (quant_score >= 60 and thesis_score <= 40) or (quant_score <= 40 and thesis_score >= 60)
    if conflict:
        confidence = "Medium-Low"
        if recommendation in {"Strong Buy", "Buy", "Strong Sell", "Sell"}:
            recommendation, status, action = "Hold / Watch", "Watch", "Await confirmation before acting."
    probability_up = round(clamp(50 + (combined_score - 50) * 0.62, 25, 82), 1)
    probability_down = round(100 - probability_up, 1)
    return {
        "combined_score": combined_score,
        "target": round(blended_target, 4),
        "expected_return": round(expected_return, 6),
        "direction": direction,
        "probability_up": probability_up,
        "probability_down": probability_down,
        "stop": round(stop, 4),
        "stop_pct": round(stop_pct, 6),
        "take": round(take, 4),
        "take_pct": round(take_pct, 6),
        "risk_reward": round(risk_reward, 2),
        "actionable": actionable,
        "recommendation": recommendation,
        "confidence": confidence,
        "position_status": status,
        "action": action,
        "signal_conflict": conflict,
    }
