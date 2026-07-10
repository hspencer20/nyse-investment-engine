# NYSE Investment Engine — v1.1

Institutional quantitative screening engine for liquid U.S. equities using public Yahoo Finance data.

## Current capabilities

- Downloads five years of adjusted daily market data through `yfinance`
- Applies minimum price and liquidity filters to the general universe
- Always analyzes the Strategic Watchlist: PPG, CPA, AMD, NVDA and QCOM
- Calculates trend, momentum, RSI, MACD, ATR, volatility and average volume
- Produces:
  - Highest Conviction Long Ideas
  - Top 20 Appreciation Opportunities
  - Highest Conviction Short Ideas
  - Top 20 Decline Risks
  - Strategic Watchlist
  - Trading Signals
- Applies a minimum actionable Risk/Reward of 2.0:1
- Keeps Target Price and Take Profit distinct
- Generates Markdown and JSON reports
- Stores separate pre-market, post-market and historical reports
- Runs automatically at 7:00 a.m. and 7:00 p.m. Panama time

## Generated files

```text
reports/latest_report.md
reports/latest_report.json
reports/latest_pre_market.md
reports/latest_pre_market.json
reports/latest_post_market.md
reports/latest_post_market.json
reports/history/YYYY-MM-DD_HHMM_PRE_MARKET.json
reports/history/YYYY-MM-DD_HHMM_POST_MARKET.json
```

## Run manually

```bash
pip install -r requirements.txt
python main.py --report-type PRE_MARKET
```

or:

```bash
python main.py --report-type POST_MARKET
```

## Data source

Yahoo Finance data accessed through the unofficial `yfinance` package. Intended for personal research and informational use.
