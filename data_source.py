from __future__ import annotations

import pandas as pd
import yfinance as yf


def download_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    data = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if data.empty:
        raise ValueError(f"No Yahoo Finance data returned for {ticker}")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing columns for {ticker}: {sorted(missing)}")

    data = data.dropna(subset=["Close"]).copy()
    if data.empty:
        raise ValueError(f"No valid closing prices for {ticker}")

    return data


def get_ticker(ticker: str) -> yf.Ticker:
    return yf.Ticker(ticker)
