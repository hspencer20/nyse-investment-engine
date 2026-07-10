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


def record(row: pd.Series) -> dict[str, Any]:
    return {
        "ticker": row["ticker"], "data_date": row["data_date"],
        "last": round(float(row["last"]), 4), "target_3m": round(float(row["target"]), 4),
        "change_dollar": round(float(row["target"] - row["last"]), 4),
        "change_percent": round(float(row["expected_return"]), 6),
        "probability_up": round(float(row["probability_up"]), 1),
        "probability_down": round(float(row["probability_down"]), 1),
        "confidence": row["confidence"], "quant_score": round(float(row["quant_score"]), 1),
        "thesis_score": round(float(row["thesis_score"]), 1),
        "combined_score": round(float(row["combined_score"]), 1),
        "direction": row["direction"], "stop_loss": round(float(row["stop"]), 4),
        "stop_loss_percent": round(float(row["stop_pct"]), 6),
        "take_profit": round(float(row["take"]), 4),
        "take_profit_percent": round(float(row["take_pct"]), 6),
        "risk_reward": round(float(row["risk_reward"]), 2),
        "actionable": bool(row["actionable"]), "recommendation": row["recommendation"],
        "position_status": row["position_status"], "action": row["action"],
        "recent_catalyst": row["recent_catalyst"], "recent_risk": row["recent_risk"],
        "recent_catalyst_risk": row["recent_catalyst_risk"], "net_thesis": row["net_thesis"],
        "signal_conflict": bool(row["signal_conflict"]),
        "avg_volume": round(float(row["avg_volume"]), 0), "liquidity_status": row["liquidity_status"],
    }


def rank_changes(current, previous):
    if not previous:
        return []
    prior = {item["ticker"]: rank for rank, item in enumerate(previous, 1)}
    return [{"ticker": item["ticker"], "current_rank": rank, "previous_rank": prior.get(item["ticker"]),
             "rank_change": None if prior.get(item["ticker"]) is None else prior[item["ticker"]] - rank}
            for rank, item in enumerate(current, 1)]


def build_payload(results: pd.DataFrame, watchlist: list[str], generated_at: datetime,
                  report_type: str, previous_payload: dict | None) -> dict:
    longs = results.sort_values(["combined_score", "probability_up"], ascending=False)
    shorts = results.sort_values(["combined_score", "probability_down"], ascending=[True, False])
    long_records = [record(row) for _, row in longs.head(20).iterrows()]
    short_records = [record(row) for _, row in shorts.head(20).iterrows()]
    strategic = results[results["ticker"].isin(watchlist)].copy()
    strategic["order"] = strategic["ticker"].map({t: i for i, t in enumerate(watchlist)})
    watch_records = [record(row) for _, row in strategic.sort_values("order").iterrows()]
    previous_longs = previous_payload.get("long_top_20") if previous_payload else None
    previous_shorts = previous_payload.get("short_top_20") if previous_payload else None
    return {
        "version": "1.1.2", "generated_at": generated_at.isoformat(), "report_type": report_type,
        "market_data_dates": sorted(set(results["data_date"].astype(str))),
        "source": "Yahoo Finance via yfinance", "horizon": "3 months",
        "universe": {"eligible_equities_analyzed": int(len(results[results["eligible_general_universe"]])),
                     "total_records_including_watchlist_exceptions": int(len(results))},
        "highest_conviction_longs": long_records[:5], "long_top_20": long_records,
        "highest_conviction_shorts": short_records[:5], "short_top_20": short_records,
        "strategic_watchlist": watch_records,
        "changes": {"long_rank_changes": rank_changes(long_records, previous_longs),
                    "short_rank_changes": rank_changes(short_records, previous_shorts)},
        "trading_signals": {
            "buy_accumulate": [x["ticker"] for x in long_records if x["actionable"] and x["direction"] == "long"][:10],
            "reduce_sell": [x["ticker"] for x in short_records if x["actionable"] and x["direction"] == "short"][:10],
            "watch": [x["ticker"] for x in watch_records if not x["actionable"] or "Watch" in x["recommendation"]],
        },
    }


def detail_row(rank, item, probability_key):
    return (f"| {rank} | {item['ticker']} | {money(item['last'])} | {money(item['target_3m'])} | "
            f"{money(item['change_dollar'], True)} ({pct(item['change_percent'])}) | {item[probability_key]:.1f}% | "
            f"{item['confidence']} | {item['quant_score']:.1f} | {item['thesis_score']:.1f} | {item['combined_score']:.1f} | "
            f"{money(item['stop_loss'])} ({pct(item['stop_loss_percent'])}) | "
            f"{money(item['take_profit'])} ({pct(item['take_profit_percent'])}) | {item['risk_reward']:.1f}:1 | "
            f"{item['recommendation']} | {item['recent_catalyst_risk'][:100]} |")


def summary_row(rank, item, probability_key):
    return (f"| {rank} | {item['ticker']} | {money(item['last'])} | {money(item['target_3m'])} | "
            f"{money(item['change_dollar'], True)} | {pct(item['change_percent'])} | {item[probability_key]:.1f}% | "
            f"{item['quant_score']:.1f} | {item['thesis_score']:.1f} | {item['combined_score']:.1f} | "
            f"{item['recommendation']} | {item['recent_catalyst_risk'][:90]} |")


def build_markdown(payload: dict) -> str:
    lines = ["# U.S. Equities Investment Committee Report", "",
             f"**Report:** {payload['report_type'].replace('_', ' ').title()}  ",
             f"**Generated:** {payload['generated_at']}  ",
             f"**Market data:** {', '.join(payload['market_data_dates'])}  ", "**Horizon:** 3 months", "",
             "## Highest Conviction Long Ideas", "",
             "| # | Ticker | Last | Target 3M | Potential | Prob. Up | Confidence | Quant | Thesis | Combined | Stop Loss | Take Profit | R/R | Recommendation | Recent Catalyst / Risk |",
             "|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|"]
    lines += [detail_row(i, x, "probability_up") for i, x in enumerate(payload["highest_conviction_longs"], 1)]
    lines += ["", "## Top 20 Appreciation Opportunities", "",
              "| # | Ticker | Last | Target 3M | Δ $ | Δ % | Prob. Up | Quant | Thesis | Combined | Recommendation | Recent Catalyst / Risk |",
              "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    lines += [summary_row(i, x, "probability_up") for i, x in enumerate(payload["long_top_20"], 1)]
    lines += ["", "## Highest Conviction Short Ideas", "",
              "| # | Ticker | Last | Target 3M | Potential | Prob. Down | Confidence | Quant | Thesis | Combined | Stop Loss | Take Profit | R/R | Recommendation | Recent Catalyst / Risk |",
              "|---:|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|"]
    lines += [detail_row(i, x, "probability_down") for i, x in enumerate(payload["highest_conviction_shorts"], 1)]
    lines += ["", "## Top 20 Decline Risks", "",
              "| # | Ticker | Last | Target 3M | Δ $ | Δ % | Prob. Down | Quant | Thesis | Combined | Recommendation | Recent Catalyst / Risk |",
              "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    lines += [summary_row(i, x, "probability_down") for i, x in enumerate(payload["short_top_20"], 1)]
    lines += ["", "## Strategic Watchlist", "",
              "| Ticker | Last | Target 3M | Δ $ | Δ % | Probability | Confidence | Quant | Thesis | Combined | Stop Loss | Take Profit | R/R | Recommendation | Status | Action | Recent Catalyst / Risk |",
              "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|---|"]
    for x in payload["strategic_watchlist"]:
        prob = x["probability_up"] if x["direction"] == "long" else x["probability_down"]
        action = x["action"] + (" Below general liquidity threshold." if x["liquidity_status"] != "Eligible" else "")
        lines.append(f"| {x['ticker']} | {money(x['last'])} | {money(x['target_3m'])} | {money(x['change_dollar'], True)} | {pct(x['change_percent'])} | {prob:.1f}% | {x['confidence']} | {x['quant_score']:.1f} | {x['thesis_score']:.1f} | {x['combined_score']:.1f} | {money(x['stop_loss'])} ({pct(x['stop_loss_percent'])}) | {money(x['take_profit'])} ({pct(x['take_profit_percent'])}) | {x['risk_reward']:.1f}:1 | {x['recommendation']} | {x['position_status']} | {action} | {x['recent_catalyst_risk'][:100]} |")
    s = payload["trading_signals"]
    lines += ["", "## Trading Signals", "", f"**Buy / Accumulate:** {', '.join(s['buy_accumulate']) or 'None'}", "",
              f"**Reduce / Sell:** {', '.join(s['reduce_sell']) or 'None'}", "", f"**Watch:** {', '.join(s['watch']) or 'None'}", "",
              "**Disclaimer:** This report is informational only and does not constitute investment or financial advice.", ""]
    return "\n".join(lines)
