# NYSE Investment Engine — v2.0

Institutional multi-factor investment engine for liquid U.S. equities using public Yahoo Finance data.

## Core model

The final investment view combines five pillars:

1. Technical
2. Fundamental
3. Events
4. Analyst Consensus
5. Risk

The engine produces:

- Technical Score
- Fundamental Score
- Event Score
- Analyst Score
- Risk Score
- Final Investment Score
- Target Price
- Stop Loss
- Take Profit
- Risk/Reward
- Recommendation
- Position Status
- Action
- Recent Catalyst / Risk
- Bull Case
- Bear Case
- Committee View

## Current scope

- Five years of daily market data
- Public Yahoo Finance company data
- General price and liquidity filters
- Permanent Strategic Watchlist:
  - PPG
  - CPA
  - AMD
  - NVDA
  - QCOM
- Pre-market and post-market reports
- Markdown and JSON output
- Historical reports
- Ranking-change tracking
- Risk/Reward filter
- Automated GitHub Actions execution

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

## Manual execution

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
