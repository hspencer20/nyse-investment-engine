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
        raise ValueError(f"No data for {ticker}")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data.dropna(subset=["Close"])
