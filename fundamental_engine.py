from __future__ import annotations

from typing import Any
import math


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def safe_info(stock) -> dict:
    try:
        return stock.info or {}
    except Exception:
        return {}


def fundamental_score(stock, last_price: float) -> dict:
    info = safe_info(stock)
    score = 50.0
    components = []

    revenue_growth = safe_number(info.get("revenueGrowth"))
    earnings_growth = safe_number(info.get("earningsGrowth"))
    roe = safe_number(info.get("returnOnEquity"))
    profit_margin = safe_number(info.get("profitMargins"))
    operating_margin = safe_number(info.get("operatingMargins"))
    debt_to_equity = safe_number(info.get("debtToEquity"))
    current_ratio = safe_number(info.get("currentRatio"))
    free_cashflow = safe_number(info.get("freeCashflow"))
    market_cap = safe_number(info.get("marketCap"))
    forward_pe = safe_number(info.get("forwardPE"))
    peg_ratio = safe_number(info.get("pegRatio"))
    beta = safe_number(info.get("beta"))

    if revenue_growth is not None:
        adj = clamp(revenue_growth * 50, -8, 8)
        score += adj
        components.append(("Revenue Growth", adj))
    if earnings_growth is not None:
        adj = clamp(earnings_growth * 45, -8, 8)
        score += adj
        components.append(("EPS Growth", adj))
    if roe is not None:
        adj = clamp((roe - 0.10) * 30, -6, 8)
        score += adj
        components.append(("ROE", adj))
    if profit_margin is not None:
        adj = clamp((profit_margin - 0.08) * 25, -5, 6)
        score += adj
        components.append(("Profit Margin", adj))
    if operating_margin is not None:
        adj = clamp((operating_margin - 0.10) * 20, -5, 5)
        score += adj
        components.append(("Operating Margin", adj))
    if debt_to_equity is not None:
        normalized = debt_to_equity / 100 if debt_to_equity > 10 else debt_to_equity
        adj = clamp((1.5 - normalized) * 3, -6, 5)
        score += adj
        components.append(("Debt", adj))
    if current_ratio is not None:
        adj = clamp((current_ratio - 1.0) * 3, -4, 4)
        score += adj
        components.append(("Liquidity", adj))
    if free_cashflow is not None and market_cap and market_cap > 0:
        fcf_yield = free_cashflow / market_cap
        adj = clamp((fcf_yield - 0.03) * 60, -5, 6)
        score += adj
        components.append(("FCF Yield", adj))
    if forward_pe is not None:
        adj = clamp((28 - forward_pe) * 0.25, -6, 5)
        score += adj
        components.append(("Forward P/E", adj))
    if peg_ratio is not None and peg_ratio > 0:
        adj = clamp((2.0 - peg_ratio) * 2.5, -4, 4)
        score += adj
        components.append(("PEG", adj))

    strongest = sorted(components, key=lambda x: x[1], reverse=True)[:2]
    weakest = sorted(components, key=lambda x: x[1])[:2]

    return {
        "fundamental_score": round(clamp(score, 0, 100), 1),
        "revenue_growth": revenue_growth,
        "earnings_growth": earnings_growth,
        "roe": roe,
        "profit_margin": profit_margin,
        "operating_margin": operating_margin,
        "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio,
        "forward_pe": forward_pe,
        "peg_ratio": peg_ratio,
        "beta": beta,
        "fundamental_strengths": [item[0] for item in strongest if item[1] > 0],
        "fundamental_risks": [item[0] for item in weakest if item[1] < 0],
    }
