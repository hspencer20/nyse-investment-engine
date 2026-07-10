from __future__ import annotations

from config import MIN_ACTIONABLE_RR, TARGET_BLEND, WEIGHTS


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_committee_view(direction: str, recommendation: str, catalyst: str, risk: str) -> str:
    if recommendation in {"Strong Buy", "Buy"}:
        return "Accumulate selectively; catalyst support remains constructive."
    if recommendation in {"Strong Sell", "Sell"}:
        return "Reduce exposure; downside risks remain dominant."
    if direction == "long":
        return "Maintain; await a stronger entry or catalyst confirmation."
    return "Avoid new position; monitor for a better risk/reward setup."


def finalize_decision(technical: dict, fundamental: dict, events: dict,
                      analyst: dict, risk: dict, metrics: dict) -> dict:
    final_score = round(
        technical["technical_score"] * WEIGHTS["technical"]
        + fundamental["fundamental_score"] * WEIGHTS["fundamental"]
        + events["event_score"] * WEIGHTS["events"]
        + analyst["analyst_score"] * WEIGHTS["analyst"]
        + risk["risk_score"] * WEIGHTS["risk"],
        1,
    )

    last = float(metrics["last"])
    model_return = clamp((final_score - 50) / 210, -0.20, 0.20)
    model_target = last * (1 + model_return)

    analyst_target = analyst.get("analyst_target_mean")
    if analyst_target and analyst_target > 0:
        target = (
            model_target * TARGET_BLEND["model"]
            + float(analyst_target) * TARGET_BLEND["analyst"]
        )
    else:
        target = model_target

    expected_return = clamp(target / last - 1, -0.22, 0.22)
    direction = "long" if expected_return >= 0 else "short"

    atr_pct = float(metrics["atr"]) / last if last else 0.05
    stop_pct_abs = clamp(max(atr_pct * 1.6, 0.02), 0.02, 0.09)
    take_pct_abs = clamp(abs(expected_return) * 0.75, 0.01, 0.16)
    risk_reward = take_pct_abs / stop_pct_abs if stop_pct_abs else 0.0
    actionable = risk_reward >= MIN_ACTIONABLE_RR

    if direction == "long":
        stop = last * (1 - stop_pct_abs)
        take = last * (1 + take_pct_abs)
        stop_pct = -stop_pct_abs
        take_pct = take_pct_abs
    else:
        stop = last * (1 + stop_pct_abs)
        take = last * (1 - take_pct_abs)
        stop_pct = stop_pct_abs
        take_pct = -take_pct_abs

    conflict = (
        (technical["technical_score"] >= 65 and events["event_score"] <= 35)
        or (technical["technical_score"] <= 35 and events["event_score"] >= 65)
        or (fundamental["fundamental_score"] >= 65 and analyst["analyst_score"] <= 35)
        or (fundamental["fundamental_score"] <= 35 and analyst["analyst_score"] >= 65)
    )

    if direction == "long":
        if final_score >= 82 and actionable and not conflict:
            recommendation, confidence = "Strong Buy", "High"
            status, action = "Increase", "Accumulate in stages."
        elif final_score >= 68 and actionable and not conflict:
            recommendation, confidence = "Buy", "Medium-High"
            status, action = "Accumulate", "Add on pullbacks."
        elif final_score >= 55:
            recommendation, confidence = "Hold / Watch", "Medium"
            status, action = "Maintain", "Maintain; await a stronger entry."
        else:
            recommendation, confidence = "Hold", "Medium"
            status, action = "Maintain", "Maintain existing exposure."
    else:
        if final_score <= 18 and actionable and not conflict:
            recommendation, confidence = "Strong Sell", "High"
            status, action = "Exit / Short", "Reduce or short only within risk limits."
        elif final_score <= 30 and actionable and not conflict:
            recommendation, confidence = "Sell", "Medium-High"
            status, action = "Reduce", "Reduce exposure."
        elif final_score < 45:
            recommendation, confidence = "Watch / Avoid New Position", "Medium"
            status, action = "Watch", "Do not initiate a new position."
        else:
            recommendation, confidence = "Hold", "Medium"
            status, action = "Maintain", "Maintain existing exposure."

    if conflict:
        confidence = "Medium-Low"
        if recommendation in {"Strong Buy", "Buy", "Strong Sell", "Sell"}:
            recommendation = "Hold / Watch"
            status = "Watch"
            action = "Await confirmation before acting."

    probability_up = round(clamp(50 + (final_score - 50) * 0.64, 24, 83), 1)
    probability_down = round(100 - probability_up, 1)

    bullish_factors = (
        fundamental.get("fundamental_strengths", [])
        + ([events["recent_catalyst"]] if events["recent_catalyst"] else [])
    )[:3]
    bearish_factors = (
        fundamental.get("fundamental_risks", [])
        + ([events["recent_risk"]] if events["recent_risk"] else [])
    )[:3]

    return {
        "final_score": final_score,
        "target": round(target, 4),
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
        "bull_case": bullish_factors or ["No material bull case identified."],
        "bear_case": bearish_factors or ["No material bear case identified."],
        "committee_view": build_committee_view(
            direction, recommendation, events["recent_catalyst"], events["recent_risk"]
        ),
    }
