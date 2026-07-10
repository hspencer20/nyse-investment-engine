from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    fast = close.ewm(span=12, adjust=False).mean()
    slow = close.ewm(span=26, adjust=False).mean()
    line = fast - slow
    signal = line.ewm(span=9, adjust=False).mean()
    return line, signal


def atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - data["Close"].shift()).abs(),
            (data["Low"] - data["Close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def calculate_metrics(data: pd.DataFrame) -> dict[str, float | str]:
    close = data["Close"].dropna()
    volume = data["Volume"].dropna()

    if len(close) < 220:
        raise ValueError("Insufficient price history")

    macd_line, macd_signal = macd(close)
    atr_series = atr(data)
    daily_returns = close.pct_change()

    rolling_peak = close.cummax()
    drawdown = close / rolling_peak - 1

    return {
        "last": float(close.iloc[-1]),
        "data_date": close.index[-1].date().isoformat(),
        "sma20": float(close.rolling(20).mean().iloc[-1]),
        "sma50": float(close.rolling(50).mean().iloc[-1]),
        "sma100": float(close.rolling(100).mean().iloc[-1]),
        "sma200": float(close.rolling(200).mean().iloc[-1]),
        "ema20": float(close.ewm(span=20, adjust=False).mean().iloc[-1]),
        "ema50": float(close.ewm(span=50, adjust=False).mean().iloc[-1]),
        "rsi14": float(rsi(close).iloc[-1]),
        "macd": float(macd_line.iloc[-1]),
        "macd_signal": float(macd_signal.iloc[-1]),
        "atr": float(atr_series.iloc[-1]),
        "avg_volume": float(volume.tail(60).mean()),
        "relative_volume": float(volume.iloc[-1] / max(volume.tail(60).mean(), 1)),
        "ret_1d": float(close.pct_change(1).iloc[-1]),
        "ret_1w": float(close.pct_change(5).iloc[-1]),
        "ret_1m": float(close.pct_change(21).iloc[-1]),
        "ret_3m": float(close.pct_change(63).iloc[-1]),
        "ret_6m": float(close.pct_change(126).iloc[-1]),
        "ret_12m": float(close.pct_change(252).iloc[-1]),
        "volatility": float(daily_returns.tail(63).std() * np.sqrt(252)),
        "max_drawdown_1y": float(drawdown.tail(252).min()),
    }
