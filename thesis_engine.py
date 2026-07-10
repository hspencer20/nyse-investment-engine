from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import yfinance as yf

from config import MAX_NEWS_ITEMS, RECENT_NEWS_DAYS

POSITIVE_TERMS = {
    "beat", "beats", "raised", "raises", "upgrade", "upgraded", "buy",
    "outperform", "contract", "partnership", "expands", "growth", "record",
    "approval", "approved", "launch", "wins", "rebound", "strong", "surge",
    "buyback", "repurchase", "guidance raised", "price target raised",
}

NEGATIVE_TERMS = {
    "miss", "misses", "cut", "cuts", "downgrade", "downgraded", "sell",
    "underperform", "investigation", "lawsuit", "recall", "delay", "weak",
    "decline", "warning", "guidance cut", "price target cut", "regulatory",
    "probe", "charges", "loss", "slump",
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_call(callable_obj, default):
    try:
        value = callable_obj()
        return default if value is None else value
    except Exception:
        return default


def _headline_text(item: dict[str, Any]) -> str:
    content = item.get("content") if isinstance(item, dict) else None
    if isinstance(content, dict):
        return f"{content.get('title', '')} {content.get('summary', '')}".strip()
    return str(item.get("title", "")) if isinstance(item, dict) else ""


def _published_at(item: dict[str, Any]) -> datetime | None:
    content = item.get("content") if isinstance(item, dict) else None
    if isinstance(content, dict):
        date_text = content.get("pubDate") or content.get("displayTime")
        if date_text:
            try:
                return datetime.fromisoformat(str(date_text).replace("Z", "+00:00"))
            except ValueError:
                pass
    timestamp = item.get("providerPublishTime") if isinstance(item, dict) else None
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None
    return None


def _news_score(news_items: list[dict[str, Any]]) -> tuple[float, str, str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_NEWS_DAYS)
    scored: list[tuple[int, str]] = []
    for item in news_items[:MAX_NEWS_ITEMS]:
        published = _published_at(item)
        if published and published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published and published < cutoff:
            continue
        text = _headline_text(item)
        lower = text.lower()
        positive = sum(1 for term in POSITIVE_TERMS if term in lower)
        negative = sum(1 for term in NEGATIVE_TERMS if term in lower)
        if text:
            scored.append((positive - negative, text[:220]))
    if not scored:
        return 50.0, "No material recent catalyst identified.", "No material recent risk identified."
    total = sum(item[0] for item in scored)
    score = clamp(50 + total * 4, 20, 80)
    bullish = max(scored, key=lambda x: x[0])
    bearish = min(scored, key=lambda x: x[0])
    catalyst = bullish[1] if bullish[0] > 0 else "No material recent catalyst identified."
    risk = bearish[1] if bearish[0] < 0 else "No material recent risk identified."
    return score, catalyst, risk


def _analyst_score(stock: yf.Ticker, last_price: float) -> tuple[float, float | None, str]:
    score = 50.0
    target_mean = None
    analyst_note = "Analyst data unavailable."
    targets = _safe_call(lambda: stock.get_analyst_price_targets(), {})
    if isinstance(targets, dict):
        target_mean = targets.get("mean") or targets.get("current")
        if target_mean:
            upside = float(target_mean) / last_price - 1
            score += clamp(upside * 100, -20, 20)
            analyst_note = f"Analyst mean target implies {upside * 100:+.1f}%."
    summary = _safe_call(lambda: stock.get_recommendations_summary(), None)
    if summary is not None and hasattr(summary, "empty") and not summary.empty:
        first = summary.iloc[0].to_dict()
        strong_buy = float(first.get("strongBuy", 0) or 0)
        buy = float(first.get("buy", 0) or 0)
        hold = float(first.get("hold", 0) or 0)
        sell = float(first.get("sell", 0) or 0)
        strong_sell = float(first.get("strongSell", 0) or 0)
        total = strong_buy + buy + hold + sell + strong_sell
        if total > 0:
            balance = (2 * strong_buy + buy - sell - 2 * strong_sell) / total
            score += clamp(balance * 15, -15, 15)
    return clamp(score, 20, 80), target_mean, analyst_note


def analyze_recent_thesis(ticker: str, last_price: float) -> dict[str, Any]:
    stock = yf.Ticker(ticker)
    news = _safe_call(lambda: stock.get_news(count=MAX_NEWS_ITEMS, tab="news"), [])
    if not news:
        news = _safe_call(lambda: stock.news, [])
    news_score, catalyst, risk = _news_score(news if isinstance(news, list) else [])
    analyst_score, analyst_target, analyst_note = _analyst_score(stock, last_price)
    thesis_score = round(news_score * 0.55 + analyst_score * 0.45, 1)
    if thesis_score >= 65:
        net_thesis = "Bullish"
    elif thesis_score <= 35:
        net_thesis = "Bearish"
    else:
        net_thesis = "Neutral"
    recent_line = catalyst if net_thesis == "Bullish" else risk if net_thesis == "Bearish" else analyst_note
    return {
        "thesis_score": thesis_score,
        "news_score": round(news_score, 1),
        "analyst_score": round(analyst_score, 1),
        "analyst_target_mean": round(float(analyst_target), 4) if analyst_target else None,
        "net_thesis": net_thesis,
        "recent_catalyst": catalyst,
        "recent_risk": risk,
        "recent_catalyst_risk": recent_line,
        "analyst_note": analyst_note,
    }
