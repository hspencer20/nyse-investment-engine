from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
import re

from config import MAX_NEWS_ITEMS, RECENT_NEWS_DAYS

EVENT_WEIGHTS = {
    "earnings": 8, "guidance": 9, "investor day": 8, "contract": 7,
    "partnership": 6, "acquisition": 7, "merger": 7, "buyback": 5,
    "repurchase": 5, "approval": 6, "launch": 4, "upgrade": 5,
    "downgrade": -5, "price target raised": 4, "price target cut": -4,
    "lawsuit": -5, "investigation": -6, "probe": -6, "recall": -7,
    "regulatory": -5, "delay": -5, "warning": -6, "miss": -6,
    "beat": 6, "raises": 5, "cuts": -5, "record": 4,
    "strong": 3, "weak": -3,
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
        title = str(content.get("title", "") or "").strip()
        summary = str(content.get("summary", "") or "").strip()
        return f"{title} {summary}".strip()
    return str(item.get("title", "") or "").strip() if isinstance(item, dict) else ""


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


def normalize_alias(alias: str) -> str:
    alias = alias.lower().strip(" ,.")
    alias = re.sub(r"\b(incorporated|inc|corp|corporation|company|holdings|group|plc|ltd)\b", "", alias)
    alias = re.sub(r"[^a-z0-9]+", " ", alias)
    return re.sub(r"\s+", " ", alias).strip()


def relevant_aliases(ticker: str, aliases: list[str]) -> list[str]:
    values = {ticker.lower()}
    for alias in aliases:
        normalized = normalize_alias(alias)
        if len(normalized) >= 3:
            values.add(normalized)
    return sorted(values, key=len, reverse=True)


def is_relevant(text: str, ticker: str, aliases: list[str]) -> bool:
    lower = text.lower()
    candidates = relevant_aliases(ticker, aliases)

    # La compañía debe aparecer en el título o en el primer tercio del texto.
    first_third = lower[:max(120, len(lower) // 3)]
    return any(alias in first_third for alias in candidates)


def clean_excerpt(text: str, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text

    shortened = text[:limit]
    last_period = max(
        shortened.rfind(". "),
        shortened.rfind("? "),
        shortened.rfind("! "),
    )

    if last_period >= 100:
        return shortened[:last_period + 1].strip()

    last_space = shortened.rfind(" ")
    if last_space > 0:
        shortened = shortened[:last_space]

    return shortened.rstrip(" ,;:-") + "…"


def event_score(stock, ticker: str, aliases: list[str]) -> dict:
    items = safe_news(stock)
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_NEWS_DAYS)
    scored: list[tuple[int, str]] = []

    for item in items[:MAX_NEWS_ITEMS]:
        dt = published_at(item)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt and dt < cutoff:
            continue

        text = headline_text(item)
        if not text or not is_relevant(text, ticker, aliases):
            continue

        lower = text.lower()
        item_score = sum(
            weight for term, weight in EVENT_WEIGHTS.items()
            if term in lower
        )
        scored.append((item_score, clean_excerpt(text)))

    if not scored:
        return {
            "event_score": 50.0,
            "recent_catalyst": "No material recent catalyst identified.",
            "recent_risk": "No material recent risk identified.",
            "event_bias": "Neutral",
            "news_items_used": 0,
        }

    net = sum(item[0] for item in scored)
    score = clamp(50 + net * 1.5, 15, 85)
    bullish = max(scored, key=lambda x: x[0])
    bearish = min(scored, key=lambda x: x[0])

    return {
        "event_score": round(score, 1),
        "recent_catalyst": (
            bullish[1]
            if bullish[0] > 0
            else "No material recent catalyst identified."
        ),
        "recent_risk": (
            bearish[1]
            if bearish[0] < 0
            else "No material recent risk identified."
        ),
        "event_bias": (
            "Bullish" if score >= 60
            else "Bearish" if score <= 40
            else "Neutral"
        ),
        "news_items_used": len(scored),
    }
