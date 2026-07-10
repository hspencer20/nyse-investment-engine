from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

def money(v):
    return f"{'+' if v > 0 else ''}${v:,.2f}"

def pct(v):
    return f"{'+' if v > 0 else ''}{v*100:.1f}%"

def rows(frame, limit=20):
    out = []
    for rank, (_, r) in enumerate(frame.head(limit).iterrows(), 1):
        out.append(
            f"| {rank} | {r['ticker']} | ${r['last']:,.2f} | ${r['target']:,.2f} | "
            f"{money(r['target']-r['last'])} | {pct(r['expected_return'])} | "
            f"{r['probability_up']:.1f}% | {r['confidence']} | {r['quant_score']:.1f} | {r['signal']} |"
        )
    return out

def build_report(df: pd.DataFrame, watchlist, output_path):
    now = datetime.now(ZoneInfo("America/Panama"))
    longs = df.sort_values(["quant_score","probability_up"], ascending=False)
    shorts = df.sort_values(["quant_score","probability_down"], ascending=[True,False])

    strategic = df[df["ticker"].isin(watchlist)].copy()
    strategic["order"] = strategic["ticker"].map({t:i for i,t in enumerate(watchlist)})
    strategic = strategic.sort_values("order")

    lines = [
        "# U.S. Equities Investment Committee Report","",
        f"**Generated:** {now:%Y-%m-%d %I:%M %p} — America/Panama  ",
        "**Horizon:** 3 months","",
        "## Market Snapshot","",
        f"- Eligible equities analyzed: **{len(df)}**",
        f"- Highest Quant Score: **{longs.iloc[0]['ticker']} ({longs.iloc[0]['quant_score']:.1f})**",
        f"- Lowest Quant Score: **{shorts.iloc[0]['ticker']} ({shorts.iloc[0]['quant_score']:.1f})**","",
        "## Highest Conviction Long Ideas","",
        "| # | Ticker | Last | Target 3M | Δ $ | Δ % | Prob. Up | Confidence | Score | Signal |",
        "|---:|---|---:|---:|---:|---:|---:|---|---:|---|",
        *rows(longs,5),"",
        "## Top 20 Appreciation Opportunities","",
        "| # | Ticker | Last | Target 3M | Δ $ | Δ % | Prob. Up | Confidence | Score | Signal |",
        "|---:|---|---:|---:|---:|---:|---:|---|---:|---|",
        *rows(longs,20),"",
        "## Highest Conviction Short Ideas","",
        "| # | Ticker | Last | Target 3M | Δ $ | Δ % | Prob. Up | Confidence | Score | Signal |",
        "|---:|---|---:|---:|---:|---:|---:|---|---:|---|",
        *rows(shorts,5),"",
        "## Top 20 Decline Risks","",
        "| # | Ticker | Last | Target 3M | Δ $ | Δ % | Prob. Up | Confidence | Score | Signal |",
        "|---:|---|---:|---:|---:|---:|---:|---|---:|---|",
        *rows(shorts,20),"",
        "## Strategic Watchlist","",
        "| Ticker | Last | Target 3M | Δ % | Stop Loss | Take Profit | R/R | Prob. Up | Score | Signal |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"
    ]

    for _, r in strategic.iterrows():
        lines.append(
            f"| {r['ticker']} | ${r['last']:,.2f} | ${r['target']:,.2f} | {pct(r['expected_return'])} | "
            f"${r['stop']:,.2f} ({pct(r['stop_pct'])}) | ${r['take']:,.2f} ({pct(r['take_pct'])}) | "
            f"{r['risk_reward']:.1f}:1 | {r['probability_up']:.1f}% | {r['quant_score']:.1f} | {r['signal']} |"
        )

    lines += [
        "","## Trading Signals","",
        f"**Buy / Accumulate:** {', '.join(longs.head(7)['ticker'].tolist())}","",
        f"**Reduce / Sell:** {', '.join(shorts.head(7)['ticker'].tolist())}","",
        "**Disclaimer:** This report is informational only and does not constitute investment or financial advice.",""
    ]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
