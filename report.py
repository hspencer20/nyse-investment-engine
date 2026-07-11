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
        "company": row.get("company", row["ticker"]),
        "sector": row.get("sector", "Not available"),
        "data_date": row["data_date"],
        "last": round(float(row["last"]), 4),
        "target_3m": round(float(row["target"]), 4),
        "change_dollar": round(float(row["target"] - row["last"]), 4),
        "change_percent": round(float(row["expected_return"]), 6),
        "probability_up": round(float(row["probability_up"]), 1),
        "probability_down": round(float(row["probability_down"]), 1),
        "confidence": row["confidence"],
        "quant_score": round(float(row.get("quant_score", row.get("technical_score", 50))), 1),
        "thesis_score": round(float(row.get("thesis_score", row.get("event_score", 50))), 1),
        "combined_score": round(float(row.get("combined_score", row.get("final_score", 50))), 1),
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
        "recent_catalyst": row.get("recent_catalyst", "No material recent catalyst identified."),
        "recent_risk": row.get("recent_risk", "No material recent risk identified."),
        "recent_catalyst_risk": row.get(
            "recent_catalyst_risk",
            row.get("recent_catalyst", "No material recent catalyst identified."),
        ),
        "net_thesis": row.get("net_thesis", "Neutral"),
        "signal_conflict": bool(row.get("signal_conflict", False)),
        "avg_volume": round(float(row["avg_volume"]), 0),
        "liquidity_status": row["liquidity_status"],
    }


def _rank_changes(
    current: list[dict[str, Any]],
    previous: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if not previous:
        return []

    previous_ranks = {
        item["ticker"]: {"rank": rank, "record": item}
        for rank, item in enumerate(previous, 1)
    }
    changes: list[dict[str, Any]] = []

    for current_rank, item in enumerate(current, 1):
        prior = previous_ranks.get(item["ticker"])
        if prior is None:
            changes.append({
                "ticker": item["ticker"],
                "current_rank": current_rank,
                "previous_rank": None,
                "rank_change": None,
                "status": "NEW",
                "signal_change": None,
                "target_change": None,
                "probability_change": None,
                "stop_loss_change": None,
                "take_profit_change": None,
                "risk_reward_change": None,
            })
            continue

        previous_rank = prior["rank"]
        previous_item = prior["record"]
        probability_key = (
            "probability_up" if item.get("direction") == "long" else "probability_down"
        )

        changes.append({
            "ticker": item["ticker"],
            "current_rank": current_rank,
            "previous_rank": previous_rank,
            "rank_change": previous_rank - current_rank,
            "status": "UNCHANGED" if previous_rank == current_rank else "MOVED",
            "signal_change": (
                None
                if previous_item.get("recommendation") == item.get("recommendation")
                else f"{previous_item.get('recommendation')} -> {item.get('recommendation')}"
            ),
            "target_change": round(
                item["target_3m"] - previous_item.get("target_3m", item["target_3m"]),
                4,
            ),
            "probability_change": round(
                item[probability_key]
                - previous_item.get(probability_key, item[probability_key]),
                1,
            ),
            "stop_loss_change": round(
                item["stop_loss"]
                - previous_item.get("stop_loss", item["stop_loss"]),
                4,
            ),
            "take_profit_change": round(
                item["take_profit"]
                - previous_item.get("take_profit", item["take_profit"]),
                4,
            ),
            "risk_reward_change": round(
                item["risk_reward"]
                - previous_item.get("risk_reward", item["risk_reward"]),
                2,
            ),
        })

    current_tickers = {item["ticker"] for item in current}
    for previous_rank, previous_item in enumerate(previous, 1):
        if previous_item["ticker"] not in current_tickers:
            changes.append({
                "ticker": previous_item["ticker"],
                "current_rank": None,
                "previous_rank": previous_rank,
                "rank_change": None,
                "status": "EXITED",
                "signal_change": None,
                "target_change": None,
                "probability_change": None,
                "stop_loss_change": None,
                "take_profit_change": None,
                "risk_reward_change": None,
            })

    return changes


def build_payload(
    results: pd.DataFrame,
    watchlist: list[str],
    generated_at: datetime,
    report_type: str,
    previous_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    score_column = "combined_score" if "combined_score" in results.columns else "final_score"
    longs = results.sort_values([score_column, "probability_up"], ascending=False)
    shorts = results.sort_values([score_column, "probability_down"], ascending=[True, False])

    long_records = [_record(row) for _, row in longs.head(20).iterrows()]
    short_records = [_record(row) for _, row in shorts.head(20).iterrows()]

    strategic = results[results["ticker"].isin(watchlist)].copy()
    strategic["watch_order"] = strategic["ticker"].map(
        {ticker: index for index, ticker in enumerate(watchlist)}
    )
    strategic = strategic.sort_values("watch_order")
    watch_records = [_record(row) for _, row in strategic.iterrows()]

    previous_longs = previous_payload.get("long_top_20") if previous_payload else None
    previous_shorts = previous_payload.get("short_top_20") if previous_payload else None

    actionable_longs = [
        item["ticker"]
        for item in long_records
        if item["actionable"] and item["direction"] == "long"
    ]
    actionable_shorts = [
        item["ticker"]
        for item in short_records
        if item["actionable"] and item["direction"] == "short"
    ]
    watch_names = [
        item["ticker"]
        for item in watch_records
        if not item["actionable"] or "Watch" in item["recommendation"]
    ]

    data_dates = sorted(set(results["data_date"].astype(str).tolist()))

    return {
        "version": "2.0.2",
        "generated_at": generated_at.isoformat(),
        "report_type": report_type,
        "market_data_dates": data_dates,
        "source": "Yahoo Finance via yfinance",
        "horizon": "3 months",
        "universe": {
            "eligible_equities_analyzed": int(
                len(results[results["eligible_general_universe"]])
            ),
            "total_records_including_watchlist_exceptions": int(len(results)),
        },
        "market_snapshot": {
            "highest_combined_score": {
                "ticker": longs.iloc[0]["ticker"],
                "score": round(float(longs.iloc[0][score_column]), 1),
            },
            "lowest_combined_score": {
                "ticker": shorts.iloc[0]["ticker"],
                "score": round(float(shorts.iloc[0][score_column]), 1),
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
            "| {rank} | {ticker} | {company} | {sector} | {last} | {target} | "
            "{delta} ({delta_pct}) | {prob:.1f}% | {confidence} | {score:.1f} | "
            "{stop} ({stop_pct}) | {take} ({take_pct}) | {rr:.1f}:1 | "
            "{recommendation} | {status} | {action} | {catalyst} | {risk} |".format(
                rank=rank,
                ticker=item["ticker"],
                company=item["company"],
                sector=item["sector"],
                last=money(item["last"]),
                target=money(item["target_3m"]),
                delta=money(item["change_dollar"], signed=True),
                delta_pct=pct(item["change_percent"]),
                prob=item[probability_key],
                confidence=item["confidence"],
                score=item["combined_score"],
                stop=money(item["stop_loss"]),
                stop_pct=pct(item["stop_loss_percent"]),
                take=money(item["take_profit"]),
                take_pct=pct(item["take_profit_percent"]),
                rr=item["risk_reward"],
                recommendation=item["recommendation"],
                status=item["position_status"],
                action=item["action"],
                catalyst=item["recent_catalyst"][:100],
                risk=item["recent_risk"][:100],
            )
        )
    return rows


def _top20_rows(items: list[dict[str, Any]], probability_key: str) -> list[str]:
    rows = []
    for rank, item in enumerate(items, 1):
        rows.append(
            "| {rank} | {ticker} | {company} | {sector} | {last} | {target} | "
            "{delta} | {delta_pct} | {prob:.1f}% | {confidence} | {score:.1f} | "
            "{recommendation} | {status} | {action} | {recent} |".format(
                rank=rank,
                ticker=item["ticker"],
                company=item["company"],
                sector=item["sector"],
                last=money(item["last"]),
                target=money(item["target_3m"]),
                delta=money(item["change_dollar"], signed=True),
                delta_pct=pct(item["change_percent"]),
                prob=item[probability_key],
                confidence=item["confidence"],
                score=item["combined_score"],
                recommendation=item["recommendation"],
                status=item["position_status"],
                action=item["action"],
                recent=item["recent_catalyst_risk"][:100],
            )
        )
    return rows


def _watchlist_rows(items: list[dict[str, Any]]) -> list[str]:
    rows = []
    for item in items:
        probability = (
            item["probability_up"]
            if item["direction"] == "long"
            else item["probability_down"]
        )
        action = item["action"]
        if item["liquidity_status"] != "Eligible":
            action += " Below general liquidity threshold."
        rows.append(
            "| {ticker} | {company} | {sector} | {last} | {target} | {delta} | "
            "{delta_pct} | {prob:.1f}% | {confidence} | {score:.1f} | "
            "{stop} ({stop_pct}) | {take} ({take_pct}) | {rr:.1f}:1 | "
            "{recommendation} | {status} | {action} | {catalyst} | {risk} |".format(
                ticker=item["ticker"],
                company=item["company"],
                sector=item["sector"],
                last=money(item["last"]),
                target=money(item["target_3m"]),
                delta=money(item["change_dollar"], signed=True),
                delta_pct=pct(item["change_percent"]),
                prob=probability,
                confidence=item["confidence"],
                score=item["combined_score"],
                stop=money(item["stop_loss"]),
                stop_pct=pct(item["stop_loss_percent"]),
                take=money(item["take_profit"]),
                take_pct=pct(item["take_profit_percent"]),
                rr=item["risk_reward"],
                recommendation=item["recommendation"],
                status=item["position_status"],
                action=action,
                catalyst=item["recent_catalyst"][:100],
                risk=item["recent_risk"][:100],
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
        f"- Highest Combined Score: **{snapshot['highest_combined_score']['ticker']} ({snapshot['highest_combined_score']['score']:.1f})**",
        f"- Lowest Combined Score: **{snapshot['lowest_combined_score']['ticker']} ({snapshot['lowest_combined_score']['score']:.1f})**",
        "",
        "## Highest Conviction Long Ideas",
        "",
        "| # | Ticker | Company | Sector | Last | Target 3M | Potential | Prob. Up | Confidence | Score | Stop Loss | Take Profit | R/R | Recommendation | Position Status | Action | Recent Catalyst | Principal Risk |",
        "|---:|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|---|---|---|",
        *_top5_rows(payload["highest_conviction_longs"], "probability_up"),
        "",
        "## Top 20 Appreciation Opportunities",
        "",
        "| # | Ticker | Company | Sector | Last | Target 3M | Δ $ | Δ % | Prob. Up | Confidence | Score | Recommendation | Position Status | Action | Recent Catalyst / Risk |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---|---|---|",
        *_top20_rows(payload["long_top_20"], "probability_up"),
        "",
        "## Highest Conviction Short Ideas",
        "",
        "| # | Ticker | Company | Sector | Last | Target 3M | Potential | Prob. Down | Confidence | Score | Stop Loss | Take Profit | R/R | Recommendation | Position Status | Action | Recent Catalyst | Principal Risk |",
        "|---:|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|---|---|---|",
        *_top5_rows(payload["highest_conviction_shorts"], "probability_down"),
        "",
        "## Top 20 Decline Risks",
        "",
        "| # | Ticker | Company | Sector | Last | Target 3M | Δ $ | Δ % | Prob. Down | Confidence | Score | Recommendation | Position Status | Action | Recent Catalyst / Risk |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---|---|---|",
        *_top20_rows(payload["short_top_20"], "probability_down"),
        "",
        "## Strategic Watchlist",
        "",
        "| Ticker | Company | Sector | Last | Target 3M | Δ $ | Δ % | Probability | Confidence | Score | Stop Loss | Take Profit | R/R | Recommendation | Position Status | Action | Recent Catalyst | Principal Risk |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|---|---|---|",
        *_watchlist_rows(payload["strategic_watchlist"]),
        "",
        "## Changes vs Previous Report",
        "",
        f"**Long ranking changes recorded:** {len(payload['changes']['long_rank_changes'])}",
        "",
        f"**Short ranking changes recorded:** {len(payload['changes']['short_rank_changes'])}",
        "",
        "## Trading Signals",
        "",
        f"**Buy / Accumulate:** {', '.join(payload['trading_signals']['buy_accumulate']) or 'None'}",
        "",
        f"**Reduce / Sell:** {', '.join(payload['trading_signals']['reduce_sell']) or 'None'}",
        "",
        f"**Watch:** {', '.join(payload['trading_signals']['watch']) or 'None'}",
        "",
        "Disclaimer: This report is informational only and does not constitute investment or financial advice.",
        "",
    ]
    return "\n".join(lines)
