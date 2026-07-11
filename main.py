from __future__ import annotations

import argparse
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from analyst_engine import analyst_score
from company_engine import company_profile
from config import (
    HISTORY_DIR,
    HISTORY_PERIOD,
    MIN_AVG_VOLUME,
    MIN_PRICE,
    REPORT_DIR,
    TIMEZONE,
    UNIVERSE,
    WATCHLIST,
)
from data_source import download_history, get_ticker
from decision_engine import finalize_decision
from event_engine import event_score
from fundamental_engine import fundamental_score
from indicators import calculate_metrics
from report import build_markdown, build_payload
from risk_engine import risk_score
from storage import read_json, report_paths, write_json, write_text
from technical_engine import technical_score
from validation import validate_payload

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report-type",
        choices=["PRE_MARKET", "POST_MARKET"],
        required=True,
    )
    return parser.parse_args()


def analyze_ticker(ticker: str, watchlist_exception: bool = False) -> dict:
    history = download_history(ticker, HISTORY_PERIOD)
    metrics = calculate_metrics(history)

    price_eligible = float(metrics["last"]) >= MIN_PRICE
    liquidity_eligible = float(metrics["avg_volume"]) >= MIN_AVG_VOLUME

    if not price_eligible:
        raise ValueError("Price below threshold")
    if not liquidity_eligible and not watchlist_exception:
        raise ValueError("Liquidity below threshold")

    stock = get_ticker(ticker)
    profile = company_profile(stock, ticker)
    technical = technical_score(metrics)
    fundamental = fundamental_score(stock, float(metrics["last"]))
    events = event_score(stock, ticker, profile["company_aliases"])
    analyst = analyst_score(stock, float(metrics["last"]))
    risk = risk_score(metrics, fundamental)
    final = finalize_decision(
        technical,
        fundamental,
        events,
        analyst,
        risk,
        metrics,
    )

    return {
        "ticker": ticker,
        **profile,
        **metrics,
        **technical,
        **fundamental,
        **events,
        **analyst,
        **risk,
        **final,
        "liquidity_status": (
            "Eligible"
            if liquidity_eligible
            else "Below general liquidity threshold"
        ),
        "eligible_general_universe": bool(
            liquidity_eligible and price_eligible
        ),
    }


def main() -> None:
    args = parse_args()
    generated_at = datetime.now(ZoneInfo(TIMEZONE))
    paths = report_paths(
        REPORT_DIR,
        HISTORY_DIR,
        args.report_type,
        generated_at,
    )
    previous_payload = read_json(paths["typed_json"])

    rows = []
    for ticker in dict.fromkeys(UNIVERSE + WATCHLIST):
        try:
            rows.append(analyze_ticker(ticker, ticker in WATCHLIST))
            logging.info("Analyzed %s", ticker)
        except Exception as exc:
            logging.warning("Skipped %s: %s", ticker, exc)

    if not rows:
        raise RuntimeError("No valid equities were analyzed")

    results = pd.DataFrame(rows)
    missing_watchlist = sorted(set(WATCHLIST).difference(results["ticker"]))
    if missing_watchlist:
        raise RuntimeError(
            f"Strategic Watchlist tickers missing: {missing_watchlist}"
        )

    payload = build_payload(
        results,
        WATCHLIST,
        generated_at,
        args.report_type,
        previous_payload,
    )
    validate_payload(payload)
    markdown = build_markdown(payload)

    write_text(paths["latest_md"], markdown)
    write_json(paths["latest_json"], payload)
    write_text(paths["typed_md"], markdown)
    write_json(paths["typed_json"], payload)
    write_json(paths["history_json"], payload)

    logging.info("==========================================")
    logging.info("NYSE Investment Engine v2.0.2")
    logging.info("Report Type     : %s", args.report_type)
    logging.info(
        "Market Date     : %s",
        payload["market_data_dates"][0],
    )
    logging.info(
        "Universe        : %s eligible (%s total)",
        payload["universe"]["eligible_equities_analyzed"],
        payload["universe"][
            "total_records_including_watchlist_exceptions"
        ],
    )
    logging.info(
        "Top Long        : %s (%.1f)",
        payload["market_snapshot"]["highest_combined_score"]["ticker"],
        payload["market_snapshot"]["highest_combined_score"]["score"],
    )
    logging.info(
        "Top Short       : %s (%.1f)",
        payload["market_snapshot"]["lowest_combined_score"]["ticker"],
        payload["market_snapshot"]["lowest_combined_score"]["score"],
    )
    logging.info("Output          : JSON + Markdown")
    logging.info("Status          : SUCCESS")
    logging.info("==========================================")
    logging.info("Generated %s report", args.report_type)


if __name__ == "__main__":
    main()
