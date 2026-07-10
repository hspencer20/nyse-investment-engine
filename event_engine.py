from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from config import MAX_NEWS_ITEMS, RECENT_NEWS_DAYS


EVENT_WEIGHTS = {
    "earnings": 8,
    "guidance": 9,
    "investor day": 8,
    "contract": 7,
    "partnership": 6,
    "acquisition": 7,
    "merger": 7,
    "buyback": 5,
    "repurchase": 5,
    "approval": 6,
    "launch": 4,
    "upgrade": 5,
    "downgrade": -5,
    "price target raised": 4,
    "price target cut": -4,
    "lawsuit": -5,
    "investigation": -6,
    "probe": -6,
    "recall": -7,
    "regulatory": -5,
    "delay": -5,
    "warning": -6,
    "miss": -6,
    "beat": 6,
    "raises": 5,
    "cuts": -5,
    "record": 4,
    "strong": 3,
    "weak": -3,
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_news(stock) -> list[dict[str, Any]]:
    try:
        items = stock.get_news(count=MAX_NEWS_ITEMS, tab="news")
        return items if isinstance(items, list) else []
    except Exception:
        try:
            items = stock.news
            return items if isinstance(items, list) else []
        except Exception:
            return []


def headline_text(item: dict[str, Any]) -> str:
    content = item.get("content") if isinstance(item, dict) else None
    if isinstance(content, dict):
        return f"{content.get('title', '')} {content.get('summary', '')}".strip()
    return str(item.get("title", "")) if isinstance(item, dict) else ""


def published_at(item: dict[str, Any]) -> datetime | None:
    content = item.get("content") if isinstance(item, dict) else None
    if isinstance(content, dict):
        raw = content.get("pubDate") or content.get("displayTime")
        if raw:
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                pass
    raw_ts = item.get("providerPublishTime") if isinstance(item, dict) else None
    if raw_ts:
        try:
            return datetime.fromtimestamp(int(raw_ts), tz=timezone.utc)
        except Exception:
            return None
    return None


def event_score(stock) -> dict:
    items = safe_news(stock)
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_NEWS_DAYS)
    scored = []

    for item in items[:MAX_NEWS_ITEMS]:
        dt = published_at(item)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt and dt < cutoff:
            continue

        text = headline_text(item)
        lower = text.lower()
        score = sum(weight for term, weight in EVENT_WEIGHTS.items() if term in lower)
        if text:
            scored.append((score, text[:240]))

    if not scored:
        return {
            "event_score": 50.0,
            "recent_catalyst": "No material recent catalyst identified.",
            "recent_risk": "No material recent risk identified.",
            "event_bias": "Neutral",
        }

    net = sum(item[0] for item in scored)
    score = clamp(50 + net * 1.5, 15, 85)
    bullish = max(scored, key=lambda x: x[0])
    bearish = min(scored, key=lambda x: x[0])

    return {
        "event_score": round(score, 1),
        "recent_catalyst": bullish[1] if bullish[0] > 0 else "No material recent catalyst identified.",
        "recent_risk": bearish[1] if bearish[0] < 0 else "No material recent risk identified.",
        "event_bias": "Bullish" if score >= 60 else "Bearish" if score <= 40 else "Neutral",
    }
