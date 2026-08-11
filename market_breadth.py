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


def fetch_breadth_bars(universe):
    """Bulk-download ~1y of daily bars for the whole universe in one
    threaded yfinance call. Returns a yfinance multi-ticker DataFrame
    (columns are a (ticker, field) MultiIndex), or None on failure."""
    if not universe:
        return None
    tickers = [u["ticker"] for u in universe]
    try:
        return yf.download(tickers, period="1y", progress=False,
                            threads=True, group_by="ticker")
    except Exception as e:
        print(f"  [breadth bars] download failed: {e}")
        return None


def compute_breadth(bars, universe, as_of_date, week_start=None):
    """Compute breadth stats using the most recent trading day on or
    before as_of_date present in bars (bars can lag by a day if run
    before Yahoo prints the latest close). Returns a dict, or None if
    bars is unusable.

    week_start (optional date string): when provided, the `movers` list
    (top_gainers/top_losers) is computed as last close vs. the last close
    strictly before week_start (i.e. the prior Friday's close — standard
    week-over-week convention) instead of the default day-over-day (last
    vs. prior close). Falls back to the first close on/after week_start
    only if no earlier close exists in the data. Advances/declines/MA%/
    52wk-high-low counts are always day-over-day and are unaffected by
    week_start."""
    if bars is None or bars.empty or not isinstance(bars.columns, pd.MultiIndex):
        return None

    target = pd.Timestamp(as_of_date)
    monday = pd.Timestamp(week_start) if week_start else None
    by_ticker = {u["ticker"]: u for u in universe}

    advances = declines = above_50 = above_200 = 0
    new_highs = new_lows = 0
    counted = 0
    movers = []  # (pct_change, ticker, company, sector)

    for ticker in sorted({t for t, _ in bars.columns}):
        try:
            closes = bars[ticker]["Close"].dropna()
        except Exception:
            continue
        closes = closes[closes.index <= target]
        if len(closes) < 2:
            continue

        last, prev = closes.iloc[-1], closes.iloc[-2]
        counted += 1
        if last > prev:
            advances += 1
        elif last < prev:
            declines += 1

        if len(closes) >= 50 and last > closes.tail(50).mean():
            above_50 += 1
        if len(closes) >= 200 and last > closes.tail(200).mean():
            above_200 += 1

        wk52 = closes.tail(252)
        if len(wk52) >= 20:
            if last >= wk52.max():
                new_highs += 1
            if last <= wk52.min():
                new_lows += 1

        mover_pct = (last / prev - 1) * 100
        if monday is not None:
            # Standard week-over-week convention: reference the last close
            # strictly BEFORE Monday (i.e. the prior Friday's close), not
            # Monday's own close — using Monday's close as the baseline
            # silently drops Monday's entire session from the "Weekly %"
            # figure and misranks movers whose big move happened Monday.
            pre_week_series = closes[closes.index < monday]
            if not pre_week_series.empty:
                week_ref = pre_week_series.iloc[-1]
                mover_pct = (last / week_ref - 1) * 100
            else:
                # No close before Monday exists (e.g. very start of the
                # dataset) — fall back to Monday's own close as the
                # reference rather than failing.
                week_ref_series = closes[closes.index >= monday]
                if not week_ref_series.empty:
                    week_ref = week_ref_series.iloc[0]
                    mover_pct = (last / week_ref - 1) * 100

        info = by_ticker.get(ticker, {})
        movers.append((mover_pct, ticker,
                        info.get("company", ""), info.get("sector", "")))

    if counted == 0:
        return None

    movers.sort(key=lambda m: m[0])
    top_losers = movers[:5]
    top_gainers = sorted(movers[-5:], key=lambda m: m[0], reverse=True)

    return {
        "advances": advances,
        "declines": declines,
        "pct_above_50dma": round(above_50 / counted * 100, 1),
        "pct_above_200dma": round(above_200 / counted * 100, 1),
        "new_52wk_highs": new_highs,
        "new_52wk_lows": new_lows,
        "universe_size": counted,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
    }


def fetch_market_breadth(as_of_date, week_start=None):
    """Top-level entry point: universe -> bulk bars -> stats. Never
    raises — returns None on any failure so callers fall back to
    'Data not available', same convention as every other fetcher in
    this pipeline (see fetch_premarket_movers in generate_report.py).

    week_start (optional): passed through to compute_breadth() so the
    weekly report path can rank movers vs. the prior Friday's close
    (week-over-week) instead of the default day-over-day comparison."""
    print("Fetching market breadth (S&P 500, yfinance bulk)...")
    try:
        universe = get_sp500_universe()
        bars = fetch_breadth_bars(universe)
        result = compute_breadth(bars, universe, as_of_date, week_start=week_start)
        if result:
            print(f"  {result['universe_size']}/{len(universe)} tickers | "
                  f"{result['advances']} adv / {result['declines']} decl | "
                  f"{result['pct_above_50dma']}% > 50DMA")
        else:
            print("  No usable breadth data.")
        return result
    except Exception as e:
        print(f"  [market breadth] failed: {e}")
        return None
