import logging
import pandas as pd
from config import HISTORY_PERIOD, MIN_AVG_VOLUME, MIN_PRICE, REPORT_PATH, UNIVERSE, WATCHLIST
from data_source import download_history
from indicators import calculate_metrics
from model import score_stock
from report import build_report

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def analyze(ticker):
    history = download_history(ticker, HISTORY_PERIOD)
    metrics = calculate_metrics(history)
    if metrics["last"] < MIN_PRICE:
        raise ValueError("Price below threshold")
    if metrics["avg_volume"] < MIN_AVG_VOLUME:
        raise ValueError("Liquidity below threshold")
    return {"ticker": ticker, **metrics, **score_stock(metrics)}

def main():
    results = []
    for ticker in dict.fromkeys(UNIVERSE + WATCHLIST):
        try:
            results.append(analyze(ticker))
            logging.info("Analyzed %s", ticker)
        except Exception as exc:
            logging.warning("Skipped %s: %s", ticker, exc)
    if not results:
        raise RuntimeError("No valid equities analyzed")
    build_report(pd.DataFrame(results), WATCHLIST, REPORT_PATH)

if __name__ == "__main__":
    main()
