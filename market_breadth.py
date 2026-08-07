"""
market_breadth.py — S&P 500 breadth statistics computed in-house from free,
bulk yfinance data.

Why not Polygon/FMP/Finnhub: Polygon's free tier caps at 5 calls/minute
(see generate_report.py's _poly_rate_limit), which makes a 500+ ticker
universe impractical (~100 minutes at 1 call/ticker). yfinance's
yf.download() batches many tickers into one threaded call instead.
"""
import io
import json
import time
from pathlib import Path

import requests
import pandas as pd
import yfinance as yf

CACHE_FILE = Path(__file__).parent / "sp500_universe_cache.json"
CACHE_MAX_AGE_DAYS = 7


def get_sp500_universe():
    """Return [{"ticker", "company", "sector"}, ...] for current S&P 500
    constituents. Cached locally for CACHE_MAX_AGE_DAYS (constituents
    change only a handful of times a year). Falls back to a stale cache
    rather than failing outright if Wikipedia is unreachable."""
    if CACHE_FILE.exists():
        age_days = (time.time() - CACHE_FILE.stat().st_mtime) / 86400
        if age_days < CACHE_MAX_AGE_DAYS:
            return json.loads(CACHE_FILE.read_text())
    try:
        r = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        table = pd.read_html(io.StringIO(r.text))[0]
        universe = [
            {
                "ticker": str(row["Symbol"]).replace(".", "-"),
                "company": str(row["Security"]),
                "sector": str(row["GICS Sector"]),
            }
            for _, row in table.iterrows()
        ]
        CACHE_FILE.write_text(json.dumps(universe))
        return universe
    except Exception as e:
        print(f"  [S&P 500 universe] fetch failed: {e}")
        if CACHE_FILE.exists():
            print("  Falling back to stale cache.")
            return json.loads(CACHE_FILE.read_text())
        return []
