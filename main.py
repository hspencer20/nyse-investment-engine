from __future__ import annotations

import argparse
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from config import HISTORY_DIR, HISTORY_PERIOD, MIN_AVG_VOLUME, MIN_PRICE, REPORT_DIR, TIMEZONE, UNIVERSE, WATCHLIST
from data_source import download_history
from decision_engine import finalize_decision
from indicators import calculate_metrics
from model import score_stock
from report import build_markdown, build_payload
from storage import read_json, report_paths, write_json, write_text
from thesis_engine import analyze_recent_thesis

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-type", choices=["PRE_MARKET", "POST_MARKET"], default="PRE_MARKET")
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
    quant = score_stock(metrics)
    thesis = analyze_recent_thesis(ticker, float(metrics["last"]))
    final = finalize_decision(quant, thesis, float(metrics["last"]))
    return {
        "ticker": ticker,
        **metrics,
        **quant,
        **thesis,
        **final,
        "liquidity_status": "Eligible" if liquidity_eligible else "Below general liquidity threshold",
        "eligible_general_universe": bool(liquidity_eligible and price_eligible),
    }


def main() -> None:
    args = parse_args()
    generated_at = datetime.now(ZoneInfo(TIMEZONE))
    paths = report_paths(REPORT_DIR, HISTORY_DIR, args.report_type, generated_at)
    previous_payload = read_json(paths["typed_json"])
    rows = []
    for ticker in dict.fromkeys(UNIVERSE + WATCHLIST):
        try:
            rows.append(analyze_ticker(ticker, watchlist_exception=ticker in WATCHLIST))
            logging.info("Analyzed %s", ticker)
        except Exception as exc:
            logging.warning("Skipped %s: %s", ticker, exc)
    if not rows:
        raise RuntimeError("No valid equities were analyzed")
    results = pd.DataFrame(rows)
    missing = sorted(set(WATCHLIST).difference(results["ticker"]))
    if missing:
        raise RuntimeError(f"Strategic Watchlist tickers missing: {missing}")
    payload = build_payload(results, WATCHLIST, generated_at, args.report_type, previous_payload)
    markdown = build_markdown(payload)
    write_text(paths["latest_md"], markdown)
    write_json(paths["latest_json"], payload)
    write_text(paths["typed_md"], markdown)
    write_json(paths["typed_json"], payload)
    write_json(paths["history_json"], payload)
    logging.info("Generated %s report", args.report_type)


if __name__ == "__main__":
    main()
