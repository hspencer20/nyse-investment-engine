# NYSE Investment Engine

Institutional quantitative investment engine for U.S. equities using public Yahoo Finance data.

## MVP capabilities
- Downloads 5 years of daily data with `yfinance`
- Applies minimum price and liquidity filters
- Calculates trend, momentum, RSI, MACD, ATR and volatility
- Produces Top 20 appreciation opportunities
- Produces Top 20 decline risks
- Always includes PPG, CPA, AMD, NVDA and QCOM
- Generates an executive Markdown report
- Runs through GitHub Actions at 7:00 a.m. and 7:00 p.m. Panama time

## Run manually
```bash
pip install -r requirements.txt
python main.py
```

Output:
```text
reports/latest_report.md
```
