from __future__ import annotations

from datetime import datetime
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
        "ticker": row["ticker"],
        "data_date": row["data_date"],
        "last": round(float(row["last"]), 4),
        "target_3m": round(float(row["target"]), 4),
        "change_dollar": round(float(row["target"] - row["last"]), 4),
        "change_percent": round(float(row["expected_return"]), 6),
        "probability_up": round(float(row["probability_up"]), 1),
        "probability_down": round(float(row["probability_down"]), 1),
        "confidence": row["confidence"],
        "quant_score": round(float(row["quant_score"]), 1),
        "direction": row["direction"],
        "stop_loss": round(float(row["stop"]), 4),
        "stop_loss_percent": round(float(row["stop_pct"]), 6),
        "take_profit": round(float(row["take"]), 4),
        "take_profit_percent": round(float(row["take_pct"]), 6),
        "risk_reward": round(float(row["risk_reward"]), 2),
        "actionable": bool(row["actionable"]),
        "recommendation": row["signal"],
        "position_status": row["position_status"],
        "action": row["action"],
        "avg_volume": round(float(row["avg_volume"]), 0),
        "liquidity_status": row["liquidity_status"],
    }


def _rank_changes(current: list[dict[str, Any]], previous: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not previous:
        return []

    previous_ranks = {item["ticker"]: rank for rank, item in enumerate(previous, 1)}
    changes = []
    for rank, item in enumerate(current, 1):
        prior_rank = previous_ranks.get(item["ticker"])
        changes.append(
            {
                "ticker": item["ticker"],
                "current_rank": rank,
                "previous_rank": prior_rank,
                "rank_change": None if prior_rank is None else prior_rank - rank,
                "status": "NEW" if prior_rank is None else "UNCHANGED" if prior_rank == rank else "MOVED",
            }
        )
    return changes


def build_payload(
    results: pd.DataFrame,
    watchlist: list[str],
    generated_at: datetime,
    report_type: str,
    previous_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    longs = results.sort_values(["quant_score", "probability_up"], ascending=False)
    shorts = results.sort_values(["quant_score", "probability_down"], ascending=[True, False])

    long_records = [_record(row) for _, row in longs.head(20).iterrows()]
    short_records = [_record(row) for _, row in shorts.head(20).iterrows()]

    strategic = results[results["ticker"].isin(watchlist)].copy()
    strategic["watch_order"] = strategic["ticker"].map({ticker: index for index, ticker in enumerate(watchlist)})
    strategic = strategic.sort_values("watch_order")
    watch_records = [_record(row) for _, row in strategic.iterrows()]

    previous_longs = previous_payload.get("long_top_20") if previous_payload else None
    previous_shorts = previous_payload.get("short_top_20") if previous_payload else None

    actionable_longs = [item["ticker"] for item in long_records if item["actionable"] and item["direction"] == "long"]
    actionable_shorts = [item["ticker"] for item in short_records if item["actionable"] and item["direction"] == "short"]
    watch_names = [item["ticker"] for item in watch_records if not item["actionable"]]

    data_dates = sorted(set(results["data_date"].astype(str).tolist()))

    return {
        "version": "1.1",
        "generated_at": generated_at.isoformat(),
        "report_type": report_type,
        "market_data_dates": data_dates,
        "source": "Yahoo Finance via yfinance",
        "horizon": "3 months",
        "universe": {
            "eligible_equities_analyzed": int(len(results[results["eligible_general_universe"]])),
            "total_records_including_watchlist_exceptions": int(len(results)),
        },
        "market_snapshot": {
            "highest_quant_score": {
                "ticker": longs.iloc[0]["ticker"],
                "score": round(float(longs.iloc[0]["quant_score"]), 1),
            },
            "lowest_quant_score": {
                "ticker": shorts.iloc[0]["ticker"],
                "score": round(float(shorts.iloc[0]["quant_score"]), 1),
            },
        },
        "highest_conviction_longs": long_records[:5],
        "long_top_20": long_records,
        "highest_conviction_shorts": short_records[:5],
        "short_top_20": short_records,
        "strategic_watchlist": watch_records,
        "changes": {
            "long_rank_changes": _rank_changes(long_records, previous_longs),
            "short_rank_changes": _rank_changes(short_records, previous_shorts),
        },
        "trading_signals": {
            "buy_accumulate": actionable_longs[:10],
            "reduce_sell": actionable_shorts[:10],
            "watch": watch_names,
        },
    }


def _top5_rows(items: list[dict[str, Any]], probability_key: str) -> list[str]:
    rows = []
    for rank, item in enumerate(items, 1):
        rows.append(
            "| {rank} | {ticker} | {last} | {target} | {delta} ({delta_pct}) | "
            "{prob:.1f}% | {confidence} | {score:.1f} | {stop} ({stop_pct}) | "
            "{take} ({take_pct}) | {rr:.1f}:1 | {recommendation} |".format(
                rank=rank,
                ticker=item["ticker"],
                last=money(item["last"]),
                target=money(item["target_3m"]),
                delta=money(item["change_dollar"], signed=True),
                delta_pct=pct(item["change_percent"]),
                prob=item[probability_key],
                confidence=item["confidence"],
                score=item["quant_score"],
                stop=money(item["stop_loss"]),
                stop_pct=pct(item["stop_loss_percent"]),
                take=money(item["take_profit"]),
                take_pct=pct(item["take_profit_percent"]),
                rr=item["risk_reward"],
                recommendation=item["recommendation"],
            )
        )
    return rows


def _top20_rows(items: list[dict[str, Any]], probability_key: str) -> list[str]:
    rows = []
    for rank, item in enumerate(items, 1):
        rows.append(
            "| {rank} | {ticker} | {last} | {target} | {delta} | {delta_pct} | "
            "{prob:.1f}% | {confidence} | {score:.1f} | {recommendation} |".format(
                rank=rank,
                ticker=item["ticker"],
                last=money(item["last"]),
                target=money(item["target_3m"]),
                delta=money(item["change_dollar"], signed=True),
                delta_pct=pct(item["change_percent"]),
                prob=item[probability_key],
                confidence=item["confidence"],
                score=item["quant_score"],
                recommendation=item["recommendation"],
            )
        )
    return rows


def _watchlist_rows(items: list[dict[str, Any]]) -> list[str]:
    rows = []
    for item in items:
        rows.append(
            "| {ticker} | {last} | {target} | {delta} | {delta_pct} | {prob:.1f}% | "
            "{confidence} | {score:.1f} | {stop} ({stop_pct}) | {take} ({take_pct}) | "
            "{rr:.1f}:1 | {recommendation} | {status} | {action} |".format(
                ticker=item["ticker"],
                last=money(item["last"]),
                target=money(item["target_3m"]),
                delta=money(item["change_dollar"], signed=True),
                delta_pct=pct(item["change_percent"]),
                prob=item["probability_up"] if item["direction"] == "long" else item["probability_down"],
                confidence=item["confidence"],
                score=item["quant_score"],
                stop=money(item["stop_loss"]),
                stop_pct=pct(item["stop_loss_percent"]),
                take=money(item["take_profit"]),
                take_pct=pct(item["take_profit_percent"]),
                rr=item["risk_reward"],
                recommendation=item["recommendation"],
                status=item["position_status"],
                action=item["action"] + (
                    " Below general liquidity threshold."
                    if item["liquidity_status"] != "Eligible"
                    else ""
                ),
            )
        )
    return rows


def build_markdown(payload: dict[str, Any]) -> str:
    snapshot = payload["market_snapshot"]
    lines = [
        "# U.S. Equities Investment Committee Report",
        "",
        f"**Report:** {payload['report_type'].replace('_', ' ').title()}  ",
        f"**Generated:** {payload['generated_at']}  ",
        f"**Market data:** {', '.join(payload['market_data_dates'])}  ",
        "**Horizon:** 3 months",
        "",
        "## Market Snapshot",
        "",
        f"- Eligible equities analyzed: **{payload['universe']['eligible_equities_analyzed']}**",
        f"- Highest Quant Score: **{snapshot['highest_quant_score']['ticker']} ({snapshot['highest_quant_score']['score']:.1f})**",
        f"- Lowest Quant Score: **{snapshot['lowest_quant_score']['ticker']} ({snapshot['lowest_quant_score']['score']:.1f})**",
        "",
        "## Highest Conviction Long Ideas",
        "",
        "| # | Ticker | Last | Target 3M | Potential | Prob. Up | Confidence | Score | Stop Loss | Take Profit | R/R | Recommendation |",
        "|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
        *_top5_rows(payload["highest_conviction_longs"], "probability_up"),
        "",
        "## Top 20 Appreciation Opportunities",
        "",
        "| # | Ticker | Last | Target 3M | Δ $ | Δ % | Prob. Up | Confidence | Score | Recommendation |",
        "|---:|---|---:|---:|---:|---:|---:|---|---:|---|",
        *_top20_rows(payload["long_top_20"], "probability_up"),
        "",
        "## Highest Conviction Short Ideas",
        "",
        "| # | Ticker | Last | Target 3M | Potential | Prob. Down | Confidence | Score | Stop Loss | Take Profit | R/R | Recommendation |",
        "|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|",
        *_top5_rows(payload["highest_conviction_shorts"], "probability_down"),
        "",
        "## Top 20 Decline Risks",
        "",
        "| # | Ticker | Last | Target 3M | Δ $ | Δ % | Prob. Down | Confidence | Score | Recommendation |",
        "|---:|---|---:|---:|---:|---:|---:|---|---:|---|",
        *_top20_rows(payload["short_top_20"], "probability_down"),
        "",
        "## Strategic Watchlist",
        "",
        "| Ticker | Last | Target 3M | Δ $ | Δ % | Probability | Confidence | Score | Stop Loss | Take Profit | R/R | Recommendation | Position Status | Action |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|---|",
        *_watchlist_rows(payload["strategic_watchlist"]),
        "",
        "## Trading Signals",
        "",
        f"**Buy / Accumulate:** {', '.join(payload['trading_signals']['buy_accumulate']) or 'None'}",
        "",
        f"**Reduce / Sell:** {', '.join(payload['trading_signals']['reduce_sell']) or 'None'}",
        "",
        f"**Watch:** {', '.join(payload['trading_signals']['watch']) or 'None'}",
        "",
        "**Disclaimer:** This report is informational only and does not constitute investment or financial advice.",
        "",
    ]
    return "\n".join(lines)
