from __future__ import annotations

from typing import Any
import pandas as pd


def money(value: float, signed: bool = False) -> str:
    sign = "+" if signed and value > 0 else ""
    return f"{sign}${value:,.2f}"


def pct(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.1f}%"


def _record(row: pd.Series) -> dict[str, Any]:
    return {
        "ticker": row["ticker"], "company": row["company"], "sector": row["sector"],
        "data_date": row["data_date"],
        "last": round(float(row["last"]), 4),
        "target_3m": round(float(row["target"]), 4),
        "change_dollar": round(float(row["target"] - row["last"]), 4),
        "change_percent": round(float(row["expected_return"]), 6),
        "probability_up": round(float(row["probability_up"]), 1),
        "probability_down": round(float(row["probability_down"]), 1),
        "confidence": row["confidence"],
        "technical_score": round(float(row["technical_score"]), 1),
        "fundamental_score": round(float(row["fundamental_score"]), 1),
        "event_score": round(float(row["event_score"]), 1),
        "analyst_score": round(float(row["analyst_score"]), 1),
        "risk_score": round(float(row["risk_score"]), 1),
        "final_score": round(float(row["final_score"]), 1),
        "direction": row["direction"],
        "stop_loss": round(float(row["stop"]), 4),
        "stop_loss_percent": round(float(row["stop_pct"]), 6),
        "take_profit": round(float(row["take"]), 4),
        "take_profit_percent": round(float(row["take_pct"]), 6),
        "risk_reward": round(float(row["risk_reward"]), 2),
        "actionable": bool(row["actionable"]),
        "recommendation": row["recommendation"],
        "position_status": row["position_status"],
        "action": row["action"],
        "recent_catalyst": row["recent_catalyst"],
        "recent_risk": row["recent_risk"],
        "bull_case": row["bull_case"],
        "bear_case": row["bear_case"],
        "committee_view": row["committee_view"],
        "signal_conflict": bool(row["signal_conflict"]),
        "avg_volume": round(float(row["avg_volume"]), 0),
        "liquidity_status": row["liquidity_status"],
    }


def build_payload(results: pd.DataFrame, watchlist: list[str], generated_at, report_type: str,
                  previous_payload: dict[str, Any] | None) -> dict[str, Any]:
    longs = results.sort_values(["final_score", "probability_up"], ascending=False)
    shorts = results.sort_values(["final_score", "probability_down"], ascending=[True, False])

    long_records = [_record(row) for _, row in longs.head(20).iterrows()]
    short_records = [_record(row) for _, row in shorts.head(20).iterrows()]

    strategic = results[results["ticker"].isin(watchlist)].copy()
    strategic["watch_order"] = strategic["ticker"].map({t: i for i, t in enumerate(watchlist)})
    strategic = strategic.sort_values("watch_order")
    watch_records = [_record(row) for _, row in strategic.iterrows()]

    return {
        "version": "2.0.1",
        "generated_at": generated_at.isoformat(),
        "report_type": report_type,
        "market_data_dates": sorted(set(results["data_date"].astype(str).tolist())),
        "source": "Yahoo Finance via yfinance",
        "horizon": "3 months",
        "universe": {
            "eligible_equities_analyzed": int(len(results[results["eligible_general_universe"]])),
            "total_records_including_watchlist_exceptions": int(len(results)),
        },
        "market_snapshot": {
            "highest_final_score": {
                "ticker": longs.iloc[0]["ticker"],
                "score": round(float(longs.iloc[0]["final_score"]), 1),
            },
            "lowest_final_score": {
                "ticker": shorts.iloc[0]["ticker"],
                "score": round(float(shorts.iloc[0]["final_score"]), 1),
            },
        },
        "highest_conviction_longs": long_records[:5],
        "long_top_20": long_records,
        "highest_conviction_shorts": short_records[:5],
        "short_top_20": short_records,
        "strategic_watchlist": watch_records,
        "changes": {
            "long_rank_changes": _rank_changes(long_records, previous_payload.get("long_top_20") if previous_payload else None),
            "short_rank_changes": _rank_changes(short_records, previous_payload.get("short_top_20") if previous_payload else None),
        },
        "trading_signals": {
            "buy_accumulate": [i["ticker"] for i in long_records if i["actionable"] and i["direction"] == "long"][:10],
            "reduce_sell": [i["ticker"] for i in short_records if i["actionable"] and i["direction"] == "short"][:10],
            "watch": [i["ticker"] for i in watch_records if not i["actionable"] or "Watch" in i["recommendation"]],
        },
    }


def build_markdown(payload: dict[str, Any]) -> str:
    def top5_rows(items, probability_key):
        rows = []
        for rank, item in enumerate(items, 1):
            rows.append(
                f"| {rank} | {item['ticker']} | {money(item['last'])} | {money(item['target_3m'])} | "
                f"{money(item['change_dollar'], True)} ({pct(item['change_percent'])}) | "
                f"{item[probability_key]:.1f}% | {item['confidence']} | {item['final_score']:.1f} | "
                f"{money(item['stop_loss'])} ({pct(item['stop_loss_percent'])}) | "
                f"{money(item['take_profit'])} ({pct(item['take_profit_percent'])}) | "
                f"{item['risk_reward']:.1f}:1 | {item['recommendation']} | "
                f"{item['recent_catalyst'][:100]} | {item['recent_risk'][:100]} |"
            )
        return rows

    def top20_rows(items, probability_key):
        rows = []
        for rank, item in enumerate(items, 1):
            rows.append(
                f"| {rank} | {item['ticker']} | {money(item['last'])} | {money(item['target_3m'])} | "
                f"{money(item['change_dollar'], True)} | {pct(item['change_percent'])} | "
                f"{item[probability_key]:.1f}% | {item['final_score']:.1f} | "
                f"{item['recommendation']} | {item['committee_view']} |"
            )
        return rows

    def watch_rows(items):
        rows = []
        for item in items:
            probability = item["probability_up"] if item["direction"] == "long" else item["probability_down"]
            action = item["action"]
            if item["liquidity_status"] != "Eligible":
                action += " Below general liquidity threshold."
            rows.append(
                f"| {item['ticker']} | {money(item['last'])} | {money(item['target_3m'])} | "
                f"{money(item['change_dollar'], True)} | {pct(item['change_percent'])} | "
                f"{probability:.1f}% | {item['confidence']} | {item['final_score']:.1f} | "
                f"{money(item['stop_loss'])} ({pct(item['stop_loss_percent'])}) | "
                f"{money(item['take_profit'])} ({pct(item['take_profit_percent'])}) | "
                f"{item['risk_reward']:.1f}:1 | {item['recommendation']} | "
                f"{item['position_status']} | {action} | {item['committee_view']} |"
            )
        return rows

    snap = payload["market_snapshot"]
    lines = [
        "# U.S. Equities Investment Committee Report", "",
        f"**Report:** {payload['report_type'].replace('_', ' ').title()}  ",
        f"**Generated:** {payload['generated_at']}  ",
        f"**Market data:** {', '.join(payload['market_data_dates'])}  ",
        "**Horizon:** 3 months", "",
        "## Market Snapshot", "",
        f"- Eligible equities analyzed: **{payload['universe']['eligible_equities_analyzed']}**",
        f"- Highest Final Score: **{snap['highest_final_score']['ticker']} ({snap['highest_final_score']['score']:.1f})**",
        f"- Lowest Final Score: **{snap['lowest_final_score']['ticker']} ({snap['lowest_final_score']['score']:.1f})**",
        "",
        "## Highest Conviction Long Ideas", "",
        "| # | Ticker | Last | Target 3M | Potential | Prob. Up | Confidence | Final Score | Stop Loss | Take Profit | R/R | Recommendation | Recent Catalyst | Recent Risk |",
        "|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|---|",
        *top5_rows(payload["highest_conviction_longs"], "probability_up"), "",
        "## Top 20 Appreciation Opportunities", "",
        "| # | Ticker | Last | Target 3M | Δ $ | Δ % | Prob. Up | Final Score | Recommendation | Committee View |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|---|",
        *top20_rows(payload["long_top_20"], "probability_up"), "",
        "## Highest Conviction Short Ideas", "",
        "| # | Ticker | Last | Target 3M | Potential | Prob. Down | Confidence | Final Score | Stop Loss | Take Profit | R/R | Recommendation | Recent Catalyst | Recent Risk |",
        "|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|---|",
        *top5_rows(payload["highest_conviction_shorts"], "probability_down"), "",
        "## Top 20 Decline Risks", "",
        "| # | Ticker | Last | Target 3M | Δ $ | Δ % | Prob. Down | Final Score | Recommendation | Committee View |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|---|",
        *top20_rows(payload["short_top_20"], "probability_down"), "",
        "## Strategic Watchlist", "",
        "| Ticker | Last | Target 3M | Δ $ | Δ % | Probability | Confidence | Final Score | Stop Loss | Take Profit | R/R | Recommendation | Position Status | Action | Committee View |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|---|---|",
        *watch_rows(payload["strategic_watchlist"]), "",
        "## Trading Signals", "",
        f"**Buy / Accumulate:** {', '.join(payload['trading_signals']['buy_accumulate']) or 'None'}", "",
        f"**Reduce / Sell:** {', '.join(payload['trading_signals']['reduce_sell']) or 'None'}", "",
        f"**Watch:** {', '.join(payload['trading_signals']['watch']) or 'None'}", "",
        "**Disclaimer:** This report is informational only and does not constitute investment or financial advice.", "",
    ]
    return "\n".join(lines)
