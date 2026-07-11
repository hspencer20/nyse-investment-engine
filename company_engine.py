from __future__ import annotations


def company_profile(stock, ticker: str) -> dict:
    try:
        info = stock.info or {}
    except Exception:
        info = {}

    company = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector") or "Not available"
    industry = info.get("industry") or "Not available"

    aliases = {ticker.lower(), company.lower()}
    for value in (info.get("shortName"), info.get("longName")):
        if value:
            aliases.add(str(value).lower())
            aliases.add(str(value).lower().replace(",", ""))

    return {
        "company": company,
        "sector": sector,
        "industry": industry,
        "company_aliases": sorted(aliases),
    }
