#!/usr/bin/env python3
"""
GlobalMarkets Investor Daily/Weekly Report Generator
Populates Open, Close, and Weekly investor report templates.

Data sources:
  Polygon.io       — Sector ETFs, BTC, ETH, Gold, Silver  (free tier)
  yfinance         — Indices, Intl Markets, VIX, HYG/LQD, WTI, Nat Gas
  Alpha Vantage    — Top Gainers / Losers                  (free tier)
  FRED API         — 10Y Yield, 2Y Yield, Fed Funds Rate, DXY
  Forex Factory    — Economic Calendar
  Finnhub          — Analyst Actions
  FMP              — Pre/After-Hours Movers
  CNN              — Fear & Greed Index

Usage:
  python generate_report.py                              # today, open + close
  python generate_report.py --date 2026-06-18            # specific date
  python generate_report.py --dates 2026-06-16 2026-06-17 2026-06-18
  python generate_report.py --type open
  python generate_report.py --type close
  python generate_report.py --type weekly                # week containing today
  python generate_report.py --type weekly --date 2026-06-16
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yfinance as yf

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPORTS_DIR = Path(__file__).parent

def load_env():
    cfg = {}
    env_file = REPORTS_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg

ENV = load_env()
POLYGON_KEY  = ENV.get("POLYGON_API_KEY", "")
AV_KEY       = ENV.get("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_KEY  = ENV.get("FINNHUB_API_KEY", "")
FMP_KEY      = ENV.get("FMP_API_KEY", "")
FRED_KEY     = ENV.get("FRED_API_KEY", "")

POLYGON_BASE = "https://api.polygon.io"
AV_BASE      = "https://www.alphavantage.co/query"
FINNHUB_BASE = "https://finnhub.io/api/v1"
FMP_BASE     = "https://financialmodelingprep.com/api/v3"
FRED_BASE    = "https://api.stlouisfed.org/fred"

# ---------------------------------------------------------------------------
# Ticker maps
# ---------------------------------------------------------------------------

INDICES = {
    "S&P 500":      "^GSPC",
    "Nasdaq":       "^IXIC",
    "Dow Jones":    "^DJI",
    "Russell 2000": "^RUT",
}

INTL_INDICES = {
    "Japan":       ("Nikkei 225",       "^N225"),
    "South Korea": ("KOSPI",            "^KS11"),
    "Germany":     ("DAX",              "^GDAXI"),
    "UK":          ("FTSE 100",         "^FTSE"),
    "Hong Kong":   ("Hang Seng",        "^HSI"),
    "China":       ("Shanghai Comp.",   "000001.SS"),
}

ETFS = {
    "XLK":  "Technology",
    "XLF":  "Financials",
    "XLV":  "Healthcare",
    "XLE":  "Energy",
    "XLY":  "Consumer Discretionary",
    "XLI":  "Industrials",
    "XLU":  "Utilities",
    "XLRE": "Real Estate",
}

CRYPTO = {
    "Bitcoin (BTC)":  "X:BTCUSD",
    "Ethereum (ETH)": "X:ETHUSD",
}

COMMODITIES_POLY = {
    "Gold (XAU)":   "C:XAUUSD",
    "Silver (XAG)": "C:XAGUSD",
}

COMMODITIES_YF = {
    "WTI Crude Oil": "CL=F",
    "Natural Gas":   "NG=F",
}

VIX_TICKERS = {
    "VIX":   "^VIX",
    "VIX9D": "^VIX9D",
}

YIELD_YF = {
    "HYG": "HYG",
    "LQD": "LQD",
}

FRED_SERIES = {
    "10Y Yield":      "DGS10",
    "2Y Yield":       "DGS2",
    "Fed Funds Rate": "FEDFUNDS",
    "DXY":            "DTWEXBGS",
}

DISCLAIMER = (
    "\n---\n\n"
    "*This report is for informational purposes only and does not constitute "
    "investment advice. All market data is sourced from publicly available "
    "information. Past performance is not indicative of future results. "
    "Please consult a licensed financial advisor before making investment decisions.*"
)

# ---------------------------------------------------------------------------
# Polygon helpers
# ---------------------------------------------------------------------------

_poly_call_times = []

def _poly_rate_limit():
    now = time.time()
    _poly_call_times[:] = [t for t in _poly_call_times if now - t < 60]
    if len(_poly_call_times) >= 5:
        sleep_for = 61 - (now - _poly_call_times[0])
        if sleep_for > 0:
            print(f"  [rate limit] waiting {sleep_for:.0f}s ...", flush=True)
            time.sleep(sleep_for)
    _poly_call_times.append(time.time())


def poly_range(ticker, start_date, end_date):
    _poly_rate_limit()
    url = (f"{POLYGON_BASE}/v2/aggs/ticker/{ticker}/range/1/day"
           f"/{start_date}/{end_date}?adjusted=true&sort=asc&limit=500"
           f"&apiKey={POLYGON_KEY}")
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        if data.get("status") not in ("OK", "DELAYED") or not data.get("results"):
            return []
        return data["results"]
    except Exception as e:
        print(f"  [Polygon error] {ticker}: {e}")
        return []


def bars_to_dict(bars):
    result = {}
    for b in bars:
        d = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        result[d] = b
    return result

# ---------------------------------------------------------------------------
# yfinance helpers
# ---------------------------------------------------------------------------

def yf_history(ticker, period="1y"):
    try:
        t = yf.Ticker(ticker)
        return t.history(period=period, interval="1d", auto_adjust=True)
    except Exception as e:
        print(f"  [yfinance error] {ticker}: {e}")
        return None


def yf_bars_to_dict(df):
    result = {}
    if df is None or df.empty:
        return result
    for idx, row in df.iterrows():
        d = idx.strftime("%Y-%m-%d")
        result[d] = {"o": round(float(row["Open"]), 4),
                     "c": round(float(row["Close"]), 4)}
    return result

# ---------------------------------------------------------------------------
# FRED helpers
# ---------------------------------------------------------------------------

def fred_latest(series_id, target_date):
    try:
        url = (f"{FRED_BASE}/series/observations"
               f"?series_id={series_id}&sort_order=desc&limit=5"
               f"&observation_end={target_date}&api_key={FRED_KEY}&file_type=json")
        r = requests.get(url, timeout=10)
        obs = r.json().get("observations", [])
        for o in obs:
            if o["value"] not in (".", ""):
                return float(o["value"]), o["date"]
    except Exception as e:
        print(f"  [FRED error] {series_id}: {e}")
    return None, None


def fetch_fred(target_date):
    print("Fetching macro data (FRED)...")
    result = {}
    for label, series in FRED_SERIES.items():
        val, date = fred_latest(series, target_date)
        result[label] = val
        print(f"  {label}: {val} ({date})")
    return result

# ---------------------------------------------------------------------------
# Alpha Vantage — Top Gainers / Losers
# ---------------------------------------------------------------------------

def fetch_gainers_losers():
    if not AV_KEY:
        return [], []
    print("Fetching top gainers/losers (Alpha Vantage)...")
    try:
        r = requests.get(AV_BASE, params={
            "function": "TOP_GAINERS_LOSERS",
            "apikey": AV_KEY,
        }, timeout=15)
        data = r.json()
        if "Information" in data or "Note" in data:
            print(f"  [AV] Rate limit: {data}")
            return [], []

        def filter_stocks(lst):
            return [x for x in lst if float(x.get("price", 0)) >= 5][:5]

        gainers = filter_stocks(data.get("top_gainers", []))
        losers  = filter_stocks(data.get("top_losers", []))
        print(f"  Gainers: {[x['ticker'] for x in gainers]}")
        print(f"  Losers:  {[x['ticker'] for x in losers]}")
        return gainers, losers
    except Exception as e:
        print(f"  [AV error]: {e}")
        return [], []

# ---------------------------------------------------------------------------
# Finnhub — Analyst Actions
# ---------------------------------------------------------------------------

def _finnhub_ok():
    if not FINNHUB_KEY:
        return False
    try:
        r = requests.get(f"{FINNHUB_BASE}/quote", params={
            "symbol": "AAPL", "token": FINNHUB_KEY
        }, timeout=8)
        return "error" not in r.json()
    except Exception:
        return False

_finnhub_valid = None

def finnhub_valid():
    global _finnhub_valid
    if _finnhub_valid is None:
        _finnhub_valid = _finnhub_ok()
        if not _finnhub_valid:
            print("  [Finnhub] Key invalid — skipping analyst actions.")
    return _finnhub_valid


def _fetch_analyst_actions_yfinance(target_date):
    """yfinance fallback: pull real upgrade/downgrade data when Finnhub is unavailable."""
    import yfinance as yf
    import pandas as pd
    watchlist = ["AAPL","MSFT","NVDA","AMZN","GOOG","META","TSLA","AVGO","NFLX",
                 "AMD","MU","WDC","JPM","GS","MS","BAC","XOM","CVX","UNH","LLY"]
    target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    # Also include yesterday for overnight actions
    prev_dt   = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).date()
    upgrades, downgrades = [], []
    seen = set()
    for ticker in watchlist:
        try:
            hist = yf.Ticker(ticker).upgrades_downgrades
            if hist is None or hist.empty:
                continue
            hist.index = pd.to_datetime(hist.index).date
            day_data = hist[hist.index >= prev_dt]
            for date_idx, row in day_data.iterrows():
                action    = str(row.get("Action", "")).lower()
                to_grade  = str(row.get("ToGrade", ""))
                from_grade= str(row.get("FromGrade", ""))
                firm      = str(row.get("GradeCompany", ""))
                key = (ticker, firm, to_grade)
                if key in seen:
                    continue
                seen.add(key)
                entry = {
                    "ticker":  ticker,
                    "company": "",
                    "from":    from_grade,
                    "to":      to_grade,
                    "firm":    firm,
                    "target":  "—",
                }
                if action in ("up", "init"):
                    upgrades.append(entry)
                elif action in ("down",):
                    downgrades.append(entry)
            time.sleep(0.15)
        except Exception:
            pass
    return upgrades[:6], downgrades[:6]


def fetch_analyst_actions(target_date):
    # Try Finnhub first (has price targets); fall back to yfinance (free, reliable)
    if finnhub_valid():
        print("Fetching analyst actions (Finnhub)...")
        watchlist = ["AAPL","MSFT","NVDA","AMZN","GOOG","META","TSLA","AVGO","NFLX",
                     "AMD","MU","WDC","JPM","GS","MS","BAC","XOM","CVX","UNH","LLY"]
        upgrades, downgrades = [], []
        seen = set()
        from_dt = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        for ticker in watchlist:
            try:
                r = requests.get(f"{FINNHUB_BASE}/stock/upgrade-downgrade", params={
                    "symbol": ticker, "from": from_dt, "to": target_date,
                    "token": FINNHUB_KEY
                }, timeout=8)
                for item in r.json():
                    key = (item.get("symbol"), item.get("action","").lower(), item.get("toGrade",""))
                    if key in seen:
                        continue
                    seen.add(key)
                    action = item.get("action", "").lower()
                    row = {
                        "ticker":  item.get("symbol",""),
                        "company": "",
                        "from":    item.get("fromGrade",""),
                        "to":      item.get("toGrade",""),
                        "firm":    item.get("company",""),
                        "target":  "",
                    }
                    if action in ("upgrade", "buy", "init"):
                        upgrades.append(row)
                    elif action in ("downgrade", "sell"):
                        downgrades.append(row)
                time.sleep(0.2)
            except Exception:
                pass
        if upgrades or downgrades:
            print(f"  Upgrades: {len(upgrades)}  Downgrades: {len(downgrades)}")
            return upgrades[:6], downgrades[:6]

    # Finnhub unavailable or returned nothing — use yfinance
    print("Fetching analyst actions (yfinance fallback)...")
    upgrades, downgrades = _fetch_analyst_actions_yfinance(target_date)
    print(f"  Upgrades: {len(upgrades)}  Downgrades: {len(downgrades)}")
    return upgrades, downgrades

# ---------------------------------------------------------------------------
# Forex Factory — Economic Calendar
# ---------------------------------------------------------------------------

FF_CALENDAR_URLS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
]

_ff_cache = {}

def _load_ff_calendar():
    if _ff_cache:
        return _ff_cache.get("events", [])
    events = []
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    for url in FF_CALENDAR_URLS:
        try:
            r = requests.get(url, timeout=15, headers=headers)
            if r.status_code == 429:
                retry = int(r.headers.get("retry-after", 60))
                print(f"  [ForexFactory] Rate limited — waiting {retry}s ...", flush=True)
                time.sleep(retry + 2)
                r = requests.get(url, timeout=15, headers=headers)
            if r.status_code == 200 and r.text.strip():
                events.extend(r.json())
        except Exception as e:
            print(f"  [ForexFactory] {url}: {e}")
    _ff_cache["events"] = events
    return events


def fetch_economic_calendar(target_date):
    print("Fetching economic calendar (Forex Factory)...")
    all_events = _load_ff_calendar()
    filtered = []
    for e in all_events:
        raw_date = e.get("date", "")
        try:
            event_date = raw_date[:10]
        except Exception:
            continue
        if event_date != target_date:
            continue
        country = e.get("country", "").upper()
        if country not in ("USD", ""):
            continue
        impact = e.get("impact", "").lower()
        if impact not in ("high", "medium"):
            continue
        try:
            dt = datetime.fromisoformat(raw_date)
            time_et = dt.strftime("%I:%M %p").lstrip("0")
        except Exception:
            time_et = ""
        filtered.append({
            "_raw_date": raw_date,
            "time":      time_et,
            "event":     e.get("title", ""),
            "forecast":  e.get("forecast", ""),
            "previous":  e.get("previous", ""),
            "actual":    e.get("actual", ""),
            "impact":    e.get("impact", "").capitalize(),
        })

    def sort_key(ev):
        try:
            return datetime.fromisoformat(ev.get("_raw_date", "1970-01-01"))
        except Exception:
            return datetime.min
    filtered.sort(key=sort_key)
    print(f"  {len(filtered)} USD high/medium impact events on {target_date}")
    return filtered

# ---------------------------------------------------------------------------
# FMP — Pre/After-Hours Movers
# ---------------------------------------------------------------------------

def _fmp_ok():
    if not FMP_KEY:
        return False
    try:
        r = requests.get(f"{FMP_BASE}/stock_market/gainers",
                         params={"apikey": FMP_KEY}, timeout=8)
        data = r.json()
        return isinstance(data, list) and len(data) > 0
    except Exception:
        return False

_fmp_valid = None

def fmp_valid():
    global _fmp_valid
    if _fmp_valid is None:
        _fmp_valid = _fmp_ok()
        if not _fmp_valid:
            print("  [FMP] Key invalid — skipping pre/after-hours movers.")
    return _fmp_valid


def fetch_premarket_movers():
    if not fmp_valid():
        return [], []
    print("Fetching pre-market movers (FMP)...")
    try:
        r = requests.get(f"{FMP_BASE}/pre-market-movers",
                         params={"apikey": FMP_KEY}, timeout=10)
        items = r.json() if isinstance(r.json(), list) else []
        gainers = sorted([x for x in items if x.get("changesPercentage", 0) > 0],
                         key=lambda x: x["changesPercentage"], reverse=True)[:5]
        losers  = sorted([x for x in items if x.get("changesPercentage", 0) < 0],
                         key=lambda x: x["changesPercentage"])[:5]
        return gainers, losers
    except Exception as e:
        print(f"  [FMP premarket error]: {e}")
        return [], []


def fetch_afterhours_movers():
    if not fmp_valid():
        return [], []
    print("Fetching after-hours movers (FMP)...")
    try:
        r = requests.get(f"{FMP_BASE}/after-hours-movers",
                         params={"apikey": FMP_KEY}, timeout=10)
        items = r.json() if isinstance(r.json(), list) else []
        gainers = sorted([x for x in items if x.get("changesPercentage", 0) > 0],
                         key=lambda x: x["changesPercentage"], reverse=True)[:5]
        losers  = sorted([x for x in items if x.get("changesPercentage", 0) < 0],
                         key=lambda x: x["changesPercentage"])[:5]
        return gainers, losers
    except Exception as e:
        print(f"  [FMP afterhours error]: {e}")
        return [], []

# ---------------------------------------------------------------------------
# CNN Fear & Greed
# ---------------------------------------------------------------------------

def fetch_fear_greed():
    print("Fetching CNN Fear & Greed...")
    try:
        r = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        data = r.json()
        fg = data.get("fear_and_greed", {})
        score  = fg.get("score", "")
        rating = fg.get("rating", "")
        label  = rating.replace("_", " ").title() if rating else ""
        score_int = round(float(score)) if score else None
        print(f"  Fear & Greed: {score_int} — {label}")
        return score_int, label
    except Exception as e:
        print(f"  [CNN F&G error]: {e}")
        return None, ""

# ---------------------------------------------------------------------------
# Calculation helpers
# ---------------------------------------------------------------------------

def pct(new, old):
    if old and old != 0:
        return round((new - old) / abs(old) * 100, 2)
    return None

def fmt_pct(val):
    if val is None:
        return ""
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"

def fmt_price(val, decimals=2):
    if val is None:
        return ""
    return f"{val:,.{decimals}f}"

def nth_prev_trading_date(bars_dict, target_date, n):
    dates = sorted(bars_dict.keys())
    before = [d for d in dates if d <= target_date]
    if not before:
        return None
    idx = len(before) - 1
    ref_idx = idx - n
    return dates[ref_idx] if ref_idx >= 0 else None


def compute_changes(bars_dict, target_date, close_key="c"):
    dates = sorted(bars_dict.keys())
    before = [d for d in dates if d <= target_date]
    if not before:
        return {}
    actual_date = before[-1]
    close = bars_dict[actual_date][close_key]
    result = {
        "close":  close,
        "open":   bars_dict[actual_date].get("o"),
        "date":   actual_date,
    }
    # YTD: compare to Dec 31 of prior year
    year = int(actual_date[:4])
    jan1 = f"{year}-01-01"
    ytd_ref = nth_prev_trading_date(bars_dict, jan1, 0)
    if ytd_ref and ytd_ref in bars_dict:
        result["ytd"] = pct(close, bars_dict[ytd_ref][close_key])
    else:
        result["ytd"] = None

    for label, n in {"daily":1, "weekly":5, "monthly":21, "3month":63, "6month":126}.items():
        ref = nth_prev_trading_date(bars_dict, actual_date, n)
        result[label] = pct(close, bars_dict[ref][close_key]) if ref and ref in bars_dict else None
    return result

# ---------------------------------------------------------------------------
# Fetch all price data (single date)
# ---------------------------------------------------------------------------

def fetch_prices(report_date):
    start = (datetime.strptime(report_date, "%Y-%m-%d") - timedelta(days=260)).strftime("%Y-%m-%d")
    data = {}

    print("Fetching indices (yfinance)...")
    for name, ticker in INDICES.items():
        df = yf_history(ticker, period="2y")
        bd = yf_bars_to_dict(df)
        ch = compute_changes(bd, report_date)
        data[name] = ch
        print(f"  {name}: close={fmt_price(ch.get('close'))} daily={fmt_pct(ch.get('daily'))}")

    print("Fetching international indices (yfinance)...")
    for country, (index_name, ticker) in INTL_INDICES.items():
        df = yf_history(ticker, period="1y")
        bd = yf_bars_to_dict(df)
        ch = compute_changes(bd, report_date)
        ch["country"] = country
        ch["index_name"] = index_name
        data[f"intl_{country}"] = ch
        print(f"  {country} {index_name}: close={fmt_price(ch.get('close'))} daily={fmt_pct(ch.get('daily'))}")

    print("Fetching sector ETFs (Polygon)...")
    for ticker, sector in ETFS.items():
        bars = poly_range(ticker, start, report_date)
        bd = bars_to_dict(bars)
        ch = compute_changes(bd, report_date)
        ch["sector"] = sector
        data[ticker] = ch
        print(f"  {ticker}: close={fmt_price(ch.get('close'))} daily={fmt_pct(ch.get('daily'))}")

    print("Fetching crypto (Polygon)...")
    for name, ticker in CRYPTO.items():
        bars = poly_range(ticker, start, report_date)
        bd = bars_to_dict(bars)
        ch = compute_changes(bd, report_date)
        data[name] = ch
        print(f"  {name}: close={fmt_price(ch.get('close'))} daily={fmt_pct(ch.get('daily'))}")

    print("Fetching Gold/Silver (Polygon)...")
    for name, ticker in COMMODITIES_POLY.items():
        bars = poly_range(ticker, start, report_date)
        bd = bars_to_dict(bars)
        ch = compute_changes(bd, report_date)
        data[name] = ch
        print(f"  {name}: close={fmt_price(ch.get('close'))} daily={fmt_pct(ch.get('daily'))}")

    print("Fetching WTI + Natural Gas (yfinance)...")
    for name, ticker in COMMODITIES_YF.items():
        df = yf_history(ticker, period="2y")
        bd = yf_bars_to_dict(df)
        ch = compute_changes(bd, report_date)
        data[name] = ch
        print(f"  {name}: close={fmt_price(ch.get('close'))} daily={fmt_pct(ch.get('daily'))}")

    print("Fetching VIX/VIX9D (yfinance)...")
    for name, ticker in VIX_TICKERS.items():
        df = yf_history(ticker, period="1y")
        bd = yf_bars_to_dict(df)
        ch = compute_changes(bd, report_date)
        data[name] = ch
        print(f"  {name}: close={fmt_price(ch.get('close'))} daily={fmt_pct(ch.get('daily'))}")

    print("Fetching HYG/LQD (yfinance)...")
    for name, ticker in YIELD_YF.items():
        df = yf_history(ticker, period="2y")
        bd = yf_bars_to_dict(df)
        ch = compute_changes(bd, report_date)
        data[name] = ch
        print(f"  {name}: close={fmt_price(ch.get('close'))} daily={fmt_pct(ch.get('daily'))}")

    return data


def fetch_bars_all(lookback_start, end_date):
    """Fetch raw bars for all tickers once; reuse across multiple dates."""
    raw = {}
    print("Fetching indices (yfinance)...")
    for name, ticker in INDICES.items():
        df = yf_history(ticker, period="2y")
        raw[name] = yf_bars_to_dict(df)
        print(f"  {name}: {len(raw[name])} bars")

    print("Fetching international indices (yfinance)...")
    for country, (index_name, ticker) in INTL_INDICES.items():
        df = yf_history(ticker, period="1y")
        raw[f"intl_{country}"] = yf_bars_to_dict(df)
        print(f"  {country}: {len(raw[f'intl_{country}'])} bars")

    print("Fetching sector ETFs (Polygon)...")
    for ticker in ETFS:
        bars = poly_range(ticker, lookback_start, end_date)
        raw[ticker] = bars_to_dict(bars)
        print(f"  {ticker}: {len(raw[ticker])} bars")

    print("Fetching crypto (Polygon)...")
    for name, ticker in CRYPTO.items():
        bars = poly_range(ticker, lookback_start, end_date)
        raw[name] = bars_to_dict(bars)
        print(f"  {name}: {len(raw[name])} bars")

    print("Fetching Gold/Silver (Polygon)...")
    for name, ticker in COMMODITIES_POLY.items():
        bars = poly_range(ticker, lookback_start, end_date)
        raw[name] = bars_to_dict(bars)
        print(f"  {name}: {len(raw[name])} bars")

    print("Fetching WTI + Natural Gas (yfinance)...")
    for name, ticker in COMMODITIES_YF.items():
        df = yf_history(ticker, period="2y")
        raw[name] = yf_bars_to_dict(df)
        print(f"  {name}: {len(raw[name])} bars")

    print("Fetching VIX/VIX9D (yfinance)...")
    for name, ticker in VIX_TICKERS.items():
        df = yf_history(ticker, period="1y")
        raw[name] = yf_bars_to_dict(df)
        print(f"  {name}: {len(raw[name])} bars")

    print("Fetching HYG/LQD (yfinance)...")
    for name, ticker in YIELD_YF.items():
        df = yf_history(ticker, period="2y")
        raw[name] = yf_bars_to_dict(df)
        print(f"  {name}: {len(raw[name])} bars")

    return raw


def compute_prices_for_date(raw_bars, report_date):
    data = {}
    for name in INDICES:
        data[name] = compute_changes(raw_bars.get(name, {}), report_date)
    for country in INTL_INDICES:
        key = f"intl_{country}"
        ch = compute_changes(raw_bars.get(key, {}), report_date)
        ch["country"] = country
        ch["index_name"] = INTL_INDICES[country][0]
        data[key] = ch
    for ticker, sector in ETFS.items():
        ch = compute_changes(raw_bars.get(ticker, {}), report_date)
        ch["sector"] = sector
        data[ticker] = ch
    for name in CRYPTO:
        data[name] = compute_changes(raw_bars.get(name, {}), report_date)
    for name in COMMODITIES_POLY:
        data[name] = compute_changes(raw_bars.get(name, {}), report_date)
    for name in COMMODITIES_YF:
        data[name] = compute_changes(raw_bars.get(name, {}), report_date)
    for name in VIX_TICKERS:
        data[name] = compute_changes(raw_bars.get(name, {}), report_date)
    for name in YIELD_YF:
        data[name] = compute_changes(raw_bars.get(name, {}), report_date)
    return data

# ---------------------------------------------------------------------------
# Yield curve helpers (2Y from FRED already in macro dict)
# ---------------------------------------------------------------------------

def compute_spread(y10, y2):
    if y10 is not None and y2 is not None:
        spread_bps = round((y10 - y2) * 100)
        return spread_bps
    return None

def spread_signal(bps):
    if bps is None:
        return ""
    if bps < 0:
        return "Inverted — recession risk"
    if bps < 50:
        return "Flat — growth concern"
    return "Normal"

# ---------------------------------------------------------------------------
# Table row builders
# ---------------------------------------------------------------------------

def idx_row_open(name, d):
    return (f"| {name} | {fmt_price(d.get('open'))} |  "
            f"| {fmt_pct(d.get('daily'))} | {fmt_pct(d.get('weekly'))} "
            f"| {fmt_pct(d.get('monthly'))} | {fmt_pct(d.get('3month'))} "
            f"| {fmt_pct(d.get('6month'))} |")

def idx_row_close(name, d):
    return (f"| {name} | {fmt_price(d.get('open'))} | {fmt_price(d.get('close'))} "
            f"| {fmt_pct(d.get('daily'))} | {fmt_pct(d.get('weekly'))} "
            f"| {fmt_pct(d.get('monthly'))} | {fmt_pct(d.get('3month'))} "
            f"| {fmt_pct(d.get('6month'))} |")

def idx_row_weekly(name, mon_open, fri_close, d):
    weekly = fmt_pct(pct(fri_close, mon_open)) if mon_open and fri_close else ""
    return (f"| {name} | {fmt_price(mon_open)} | {fmt_price(fri_close)} "
            f"| {weekly} | {fmt_pct(d.get('monthly'))} | {fmt_pct(d.get('3month'))} "
            f"| {fmt_pct(d.get('6month'))} | {fmt_pct(d.get('ytd'))} |")

def asset_row_open(name, d):
    return (f"| {name} | {fmt_price(d.get('open'))} |  "
            f"| {fmt_pct(d.get('daily'))} | {fmt_pct(d.get('weekly'))} "
            f"| {fmt_pct(d.get('monthly'))} | {fmt_pct(d.get('3month'))} "
            f"| {fmt_pct(d.get('6month'))} |")

def asset_row_close(name, d):
    return (f"| {name} | {fmt_price(d.get('open'))} | {fmt_price(d.get('close'))} "
            f"| {fmt_pct(d.get('daily'))} | {fmt_pct(d.get('weekly'))} "
            f"| {fmt_pct(d.get('monthly'))} | {fmt_pct(d.get('3month'))} "
            f"| {fmt_pct(d.get('6month'))} |")

def asset_row_weekly(name, mon_open, fri_close, d):
    weekly = fmt_pct(pct(fri_close, mon_open)) if mon_open and fri_close else ""
    return (f"| {name} | {fmt_price(mon_open)} | {fmt_price(fri_close)} "
            f"| {weekly} | {fmt_pct(d.get('monthly'))} | {fmt_pct(d.get('3month'))} "
            f"| {fmt_pct(d.get('6month'))} | {fmt_pct(d.get('ytd'))} |")

def etf_row_open(ticker, d):
    sector = d.get("sector", ticker)
    return (f"| {sector} | {ticker} | {fmt_price(d.get('open'))} |  "
            f"| {fmt_pct(d.get('daily'))} | {fmt_pct(d.get('weekly'))} "
            f"| {fmt_pct(d.get('monthly'))} | {fmt_pct(d.get('3month'))} "
            f"| {fmt_pct(d.get('6month'))} |")

def etf_row_close(ticker, d):
    sector = d.get("sector", ticker)
    return (f"| {sector} | {ticker} | {fmt_price(d.get('open'))} | {fmt_price(d.get('close'))} "
            f"| {fmt_pct(d.get('daily'))} | {fmt_pct(d.get('weekly'))} "
            f"| {fmt_pct(d.get('monthly'))} | {fmt_pct(d.get('3month'))} "
            f"| {fmt_pct(d.get('6month'))} |")

def etf_row_weekly(ticker, mon_open, fri_close, d):
    sector = d.get("sector", ticker)
    weekly = fmt_pct(pct(fri_close, mon_open)) if mon_open and fri_close else ""
    sp_weekly = d.get("weekly")
    rel = ""
    if sp_weekly is not None:
        raw_weekly = pct(fri_close, mon_open) if mon_open and fri_close else None
        if raw_weekly is not None:
            rel_val = round(raw_weekly - sp_weekly, 2)
            rel = f"+{rel_val:.2f}%" if rel_val >= 0 else f"{rel_val:.2f}%"
    return (f"| {sector} | {ticker} | {fmt_price(mon_open)} | {fmt_price(fri_close)} "
            f"| {weekly} | {fmt_pct(d.get('monthly'))} | {fmt_pct(d.get('3month'))} "
            f"| {fmt_pct(d.get('6month'))} | {rel} |")

def intl_row(country, d):
    index_name = d.get("index_name", "")
    return f"| {country} | {index_name} | {fmt_price(d.get('close'))} | {fmt_pct(d.get('daily'))} | |"

def gainer_loser_rows(items, is_gainer=True):
    rows = []
    for i, x in enumerate(items, 1):
        ticker  = x.get("ticker") or x.get("symbol", "")
        pct_chg = x.get("change_percentage") or x.get("changesPercentage", "")
        price   = x.get("price", "")
        rows.append(f"| {i} | {ticker} | | {price} | {pct_chg} | | |")
    while len(rows) < 5:
        rows.append("| | | | | | | |")
    return rows

def analyst_rows(items):
    rows = []
    for x in items:
        rows.append(f"| {x['ticker']} | {x['company']} | {x['from']} | {x['to']} | {x['firm']} | {x['target']} | |")
    if not rows:
        rows = ["| — | *No actions reported today* | — | — | — | — | — |"]
    return rows

def analyst_rows_no_reaction(items):
    rows = []
    for x in items:
        rows.append(f"| {x['ticker']} | {x['company']} | {x['from']} | {x['to']} | {x['firm']} | {x['target']} |")
    if not rows:
        rows = ["| — | *No actions reported today* | — | — | — | — |"]
    return rows

def econ_rows(events, include_actual=False):
    rows = []
    for e in events:
        t      = e.get("time", "")
        name   = e.get("event", "")
        actual = e.get("actual", "")
        est    = e.get("forecast", "")
        prev   = e.get("previous", "")
        impact = e.get("impact", "").capitalize()
        if include_actual:
            beat_miss = ""
            if actual and est:
                try:
                    a = float(actual.replace("%","").replace("K","000").replace("M","000000"))
                    f = float(est.replace("%","").replace("K","000").replace("M","000000"))
                    beat_miss = "Beat" if a > f else ("Miss" if a < f else "In Line")
                except Exception:
                    pass
            rows.append(f"| {t} | {name} | {actual} | {est} | {prev} | {beat_miss} | |")
        else:
            rows.append(f"| {t} | {name} | {est} | {prev} | {impact} |")
    if include_actual:
        while len(rows) < 3:
            rows.append("| | | | | | | |")
    else:
        while len(rows) < 3:
            rows.append("| | | | | High / Med / Low |")
    return rows

def mover_rows(items):
    rows = []
    for x in items:
        ticker  = x.get("ticker") or x.get("symbol", "")
        name    = x.get("companyName") or x.get("name", "")
        pct_chg = x.get("change_percentage") or x.get("changesPercentage", "")
        rows.append(f"| {ticker} | {name} | {pct_chg} | |")
    while len(rows) < 3:
        rows.append("| | | | |")
    return rows

def vix_signal(val):
    if val is None:
        return ""
    if val > 30:
        return "Extreme Fear — hedging spike"
    if val > 20:
        return "Elevated — risk-off"
    if val > 15:
        return "Moderate"
    return "Low — complacency"

def fg_label_detail(score):
    if score is None:
        return ""
    if score <= 25:
        return "Extreme Fear"
    if score <= 45:
        return "Fear"
    if score <= 55:
        return "Neutral"
    if score <= 75:
        return "Greed"
    return "Extreme Greed"

# ---------------------------------------------------------------------------
# Open report builder
# ---------------------------------------------------------------------------

def build_open_report(report_date, prices, macro, pre_gainers, pre_losers,
                      upgrades, downgrades, econ_events, fg_score, fg_label):
    fdate  = datetime.strptime(report_date, "%Y-%m-%d").strftime("%m-%d-%y")
    dstr   = datetime.strptime(report_date, "%Y-%m-%d").strftime("%B %-d, %Y")
    dow    = datetime.strptime(report_date, "%Y-%m-%d").strftime("%A")
    now_et = datetime.now().strftime("%I:%M %p")

    y10  = macro.get("10Y Yield")
    y2   = macro.get("2Y Yield")
    fed  = macro.get("Fed Funds Rate")
    dxy  = macro.get("DXY")
    spread_bps = compute_spread(y10, y2)

    yield_val = f"{y10:.2f}%" if y10 else ""
    y2_val    = f"{y2:.2f}%" if y2 else ""
    fed_val   = f"{fed:.2f}%" if fed else ""
    dxy_val   = f"{dxy:,.2f}" if dxy else ""
    spread_str = f"{spread_bps:+d} bps" if spread_bps is not None else ""
    spread_sig = spread_signal(spread_bps)

    hyg = prices.get("HYG", {})
    lqd = prices.get("LQD", {})
    vix  = prices.get("VIX", {})
    vix9 = prices.get("VIX9D", {})
    vix_val  = vix.get("close")
    vix9_val = vix9.get("close")
    vix_spread = round(vix9_val - vix_val, 2) if vix_val and vix9_val else None

    fg_str = f"{fg_score} — {fg_label or fg_label_detail(fg_score)}" if fg_score else ""

    L = []
    L += [
        f"# Market Open Report — {dstr} ({dow})",
        f"**Report Type:** Open",
        f"**Generated:** {now_et} ET",
        f"**Market Status:** Pre-Market / Opening",
        "", "---", "",
        "## Market Tone",
        "**Overall:** Bullish / Cautiously Bullish / Neutral / Cautious / Bearish",
        "",
        "**TL;DR:**",
        "- ",
        "- ",
        "- ",
        "- ",
        "", "---", "",
        "## International Markets — Overnight",
        "",
        "| Market | Index | Close | Daily % | Note |",
        "|--------|-------|-------|---------|------|",
    ]
    for country in INTL_INDICES:
        L.append(intl_row(country, prices.get(f"intl_{country}", {})))

    L += ["", "---", "",
        "## Major Indices — Open", "",
        "| Index | Open | Prev. Close | Daily % | Weekly % | Monthly % | 3 Month % | 6 Month % |",
        "|-------|------|-------------|---------|----------|-----------|-----------|-----------|",
    ]
    for name in INDICES:
        L.append(idx_row_open(name, prices.get(name, {})))

    L += ["", "---", "",
        "## Crypto — Open", "",
        "| Asset | Open | Prev. Close | Daily % | Weekly % | Monthly % | 3 Month % | 6 Month % |",
        "|-------|------|-------------|---------|----------|-----------|-----------|-----------|",
    ]
    for name in CRYPTO:
        L.append(asset_row_open(name, prices.get(name, {})))

    L += ["", "---", "",
        "## Commodities — Open", "",
        "| Asset | Open | Prev. Close | Daily % | Weekly % | Monthly % | 3 Month % | 6 Month % |",
        "|-------|------|-------------|---------|----------|-----------|-----------|-----------|",
    ]
    for name in list(COMMODITIES_POLY) + list(COMMODITIES_YF):
        L.append(asset_row_open(name, prices.get(name, {})))

    L += ["", "---", "",
        "## Sector ETFs — Open", "",
        "| Sector | ETF | Open | Prev. Close | Daily % | Weekly % | Monthly % | 3 Month % | 6 Month % |",
        "|--------|-----|------|-------------|---------|----------|-----------|-----------|-----------|",
    ]
    for ticker in ETFS:
        L.append(etf_row_open(ticker, prices.get(ticker, {})))

    L += ["", "---", "",
        "## Volatility & Options Sentiment", "",
        "| Indicator | Value | Signal |",
        "|-----------|-------|--------|",
        f"| VIX (30-day implied vol) | {fmt_price(vix_val)} | {vix_signal(vix_val)} |",
        f"| VIX9D (9-day implied vol) | {fmt_price(vix9_val)} | |",
        f"| VIX9D vs VIX Spread | {fmt_price(vix_spread)} | {'Backwardation = short-term fear spike' if vix_spread and vix_spread > 0 else ''} |",
        "| Equity Put/Call Ratio | | Elevated > 1.1 (bearish), Low < 0.7 (complacent) |",
        "| Total Put/Call Ratio | | |",
    ]

    L += ["", "---", "",
        "## Market Breadth", "",
        "| Indicator | Value | Signal |",
        "|-----------|-------|--------|",
        "| NYSE Advance / Decline | / | Breadth bullish / bearish |",
        "| S&P 500 Above 50-Day MA | % | Healthy > 60% |",
        "| S&P 500 Above 200-Day MA | % | Bull market > 70% |",
        "| NYSE New 52-Week Highs | | |",
        "| NYSE New 52-Week Lows | | |",
        "| Nasdaq New 52-Week Highs | | |",
        "| Nasdaq New 52-Week Lows | | |",
    ]

    L += ["", "---", "",
        "## Yield Curve & Credit", "",
        "| Indicator | Value | Daily Chg | Signal |",
        "|-----------|-------|-----------|--------|",
        f"| 2-Year Treasury Yield | {y2_val} | bps | Most Fed-sensitive tenor |",
        f"| 10-Year Treasury Yield | {yield_val} | bps | Long-term growth / inflation |",
        f"| 2Y / 10Y Spread | {spread_str} | | {spread_sig} |",
        f"| HYG (High Yield Corp Bond) | {fmt_price(hyg.get('open'))} | {fmt_pct(hyg.get('daily'))} | Risk appetite proxy |",
        f"| LQD (Inv. Grade Corp Bond) | {fmt_price(lqd.get('open'))} | {fmt_pct(lqd.get('daily'))} | Credit quality gauge |",
    ]

    L += ["", "---", "",
        "## Earnings Calendar — This Week", "",
        "| Day | Ticker | Company | Time | EPS Est | Rev Est | Implied Move |",
        "|-----|--------|---------|------|---------|---------|--------------|",
        "| Mon | | | Pre / After | | | ±% |",
        "| Tue | | | | | | |",
        "| Wed | | | | | | |",
        "| Thu | | | | | | |",
        "| Fri | | | | | | |",
    ]

    L += ["", "---", "",
        "## Today's Economic Calendar", "",
        "| Time (ET) | Event | Forecast | Previous | Importance |",
        "|-----------|-------|----------|----------|------------|",
    ]
    L += econ_rows(econ_events)

    L += ["", "---", "",
        "## Fed Watch", "",
        f"- **Next FOMC Meeting:**",
        f"- **Current Fed Funds Rate:** {fed_val}",
        f"- **Overnight Fed Commentary:**",
        f"- **Rate Change Probability (CME FedWatch):**",
    ]

    L += ["", "---", "",
        "## Pre-Market Movers", "",
        "### Pre-Market Gainers",
        "| Ticker | Company | % Change | Catalyst |",
        "|--------|---------|----------|---------|",
    ]
    L += mover_rows(pre_gainers)
    L += ["", "### Pre-Market Losers",
        "| Ticker | Company | % Change | Catalyst |",
        "|--------|---------|----------|---------|",
    ]
    L += mover_rows(pre_losers)

    L += ["", "---", "",
        "## Analyst Actions Overnight", "",
        "### Upgrades",
        "| Ticker | Company | From | To | Firm | New Price Target |",
        "|--------|---------|------|----|------|-----------------|",
    ]
    L += analyst_rows_no_reaction(upgrades)
    L += ["", "### Downgrades",
        "| Ticker | Company | From | To | Firm | New Price Target |",
        "|--------|---------|------|----|------|-----------------|",
    ]
    L += analyst_rows_no_reaction(downgrades)

    L += ["", "---", "",
        "## Geopolitical & Macro Developments", "",
        "- **Global:**",
        "- **US:**",
        "- **Energy Markets:**",
        f"- **Currency (DXY):** {dxy_val}",
        f"- **Bond Market (10Y Yield):** {yield_val}",
    ]

    L += ["", "---", "",
        "## Morning Setup — Key Levels to Watch", "",
        "| Index / Asset | Support | Resistance | Key Level | Notes |",
        "|---------------|---------|------------|-----------|-------|",
        "| S&P 500 | | | | |",
        "| Nasdaq | | | | |",
        "| BTC | | | | |",
        "| Gold | | | | |",
    ]

    L += ["", "---", "",
        "## Sentiment Gauges", "",
        f"- **CNN Fear & Greed Index:** {fg_str}",
        "- **AAII Sentiment (latest weekly):** Bulls  % | Bears  % | Neutral  %",
        "- **Reading:**",
    ]

    L += ["", "---", "",
        "## 1. Market Summary", "",
        "[Fill in]", "", "---", "",
        "## 2. Opportunities", "",
        "- ",
        "- ",
        "- ",
        "", "---", "",
        "## 3. Risks", "",
        "- ",
        "- ",
        "- ",
    ]

    L.append(DISCLAIMER)
    L.append(f"\n*File: `Open/Open_{fdate}.md` | Next: `Close/Close_{fdate}.md`*")

    return "\n".join(L)

# ---------------------------------------------------------------------------
# Close report builder
# ---------------------------------------------------------------------------

def build_close_report(report_date, prices, macro, gainers, losers,
                       ah_gainers, ah_losers, upgrades, downgrades, econ_events,
                       fg_score, fg_label):
    fdate  = datetime.strptime(report_date, "%Y-%m-%d").strftime("%m-%d-%y")
    dstr   = datetime.strptime(report_date, "%Y-%m-%d").strftime("%B %-d, %Y")
    dow    = datetime.strptime(report_date, "%Y-%m-%d").strftime("%A")
    now_et = datetime.now().strftime("%I:%M %p")

    y10  = macro.get("10Y Yield")
    y2   = macro.get("2Y Yield")
    fed  = macro.get("Fed Funds Rate")
    dxy  = macro.get("DXY")
    spread_bps = compute_spread(y10, y2)

    yield_val  = f"{y10:.2f}%" if y10 else ""
    y2_val     = f"{y2:.2f}%" if y2 else ""
    fed_val    = f"{fed:.2f}%" if fed else ""
    dxy_val    = f"{dxy:,.2f}" if dxy else ""
    spread_str = f"{spread_bps:+d} bps" if spread_bps is not None else ""
    spread_sig = spread_signal(spread_bps)

    hyg = prices.get("HYG", {})
    lqd = prices.get("LQD", {})
    vix  = prices.get("VIX", {})
    vix9 = prices.get("VIX9D", {})
    vix_val  = vix.get("close")
    vix9_val = vix9.get("close")
    vix_spread = round(vix9_val - vix_val, 2) if vix_val and vix9_val else None

    fg_str = f"{fg_score} — {fg_label or fg_label_detail(fg_score)}" if fg_score else ""

    L = []
    L += [
        f"# Market Close Report — {dstr} ({dow})",
        f"**Report Type:** Close",
        f"**Generated:** {now_et} ET",
        f"**Market Status:** Closed",
        "", "---", "",
        "## Market Tone",
        "**Overall:** Bullish / Cautiously Bullish / Neutral / Cautious / Bearish",
        "",
        "**TL;DR:**",
        "- ",
        "- ",
        "- ",
        "- ",
        "", "---", "",
        "## Major Indices — Final", "",
        "| Index | Open | Close | Daily % | Weekly % | Monthly % | 3 Month % | 6 Month % |",
        "|-------|------|-------|---------|----------|-----------|-----------|-----------|",
    ]
    for name in INDICES:
        L.append(idx_row_close(name, prices.get(name, {})))

    L += ["", "---", "",
        "## Crypto — 4PM ET Snapshot", "",
        "| Asset | Open | Close | Daily % | Weekly % | Monthly % | 3 Month % | 6 Month % |",
        "|-------|------|-------|---------|----------|-----------|-----------|-----------|",
    ]
    for name in CRYPTO:
        L.append(asset_row_close(name, prices.get(name, {})))

    L += ["", "---", "",
        "## Commodities — Close", "",
        "| Asset | Open | Close | Daily % | Weekly % | Monthly % | 3 Month % | 6 Month % |",
        "|-------|------|-------|---------|----------|-----------|-----------|-----------|",
    ]
    for name in list(COMMODITIES_POLY) + list(COMMODITIES_YF):
        L.append(asset_row_close(name, prices.get(name, {})))

    L += ["", "---", "",
        "## Sector ETFs — Close", "",
        "| Sector | ETF | Open | Close | Daily % | Weekly % | Monthly % | 3 Month % | 6 Month % |",
        "|--------|-----|------|-------|---------|----------|-----------|-----------|-----------|",
    ]
    for ticker in ETFS:
        L.append(etf_row_close(ticker, prices.get(ticker, {})))

    L += ["", "---", "",
        "## Volatility & Options Sentiment", "",
        "| Indicator | Value | Change | Signal |",
        "|-----------|-------|--------|--------|",
        f"| VIX Close (30-day implied vol) | {fmt_price(vix_val)} | | {vix_signal(vix_val)} |",
        f"| VIX9D Close (9-day implied vol) | {fmt_price(vix9_val)} | | |",
        f"| VIX9D vs VIX Spread | {fmt_price(vix_spread)} | | {'Backwardation = fear spike' if vix_spread and vix_spread > 0 else ''} |",
        "| Equity Put/Call Ratio (close) | | | Elevated > 1.1 (fear), Low < 0.7 (complacency) |",
        "| Total Put/Call Ratio (close) | | | |",
    ]

    L += ["", "---", "",
        "## Market Breadth", "",
        "| Indicator | Value | Signal |",
        "|-----------|-------|--------|",
        "| NYSE Advance / Decline | / | Breadth bullish / bearish |",
        "| S&P 500 Above 50-Day MA | % | Healthy > 60% |",
        "| S&P 500 Above 200-Day MA | % | Bull market > 70% |",
        "| NYSE New 52-Week Highs | | |",
        "| NYSE New 52-Week Lows | | |",
        "| Nasdaq New 52-Week Highs | | |",
        "| Nasdaq New 52-Week Lows | | |",
    ]

    L += ["", "---", "",
        "## Yield Curve & Credit", "",
        "| Indicator | Value | Daily Chg | Signal |",
        "|-----------|-------|-----------|--------|",
        f"| 2-Year Treasury Yield | {y2_val} | bps | Most Fed-sensitive tenor |",
        f"| 10-Year Treasury Yield | {yield_val} | bps | Long-term growth / inflation |",
        f"| 2Y / 10Y Spread | {spread_str} | | {spread_sig} |",
        f"| HYG (High Yield Corp Bond) | {fmt_price(hyg.get('close'))} | {fmt_pct(hyg.get('daily'))} | Risk appetite proxy |",
        f"| LQD (Inv. Grade Corp Bond) | {fmt_price(lqd.get('close'))} | {fmt_pct(lqd.get('daily'))} | Credit quality gauge |",
    ]

    L += ["", "---", "",
        "## Top Gainers (S&P 500 / Market)", "",
        "| Rank | Ticker | Company | Close | Daily % | Volume vs Avg | Catalyst |",
        "|------|--------|---------|-------|---------|---------------|---------|",
    ]
    L += gainer_loser_rows(gainers, True)

    L += ["", "---", "",
        "## Top Losers (S&P 500 / Market)", "",
        "| Rank | Ticker | Company | Close | Daily % | Volume vs Avg | Catalyst |",
        "|------|--------|---------|-------|---------|---------------|---------|",
    ]
    L += gainer_loser_rows(losers, False)

    L += ["", "---", "",
        "## Analyst Actions — Today", "",
        "### Upgrades",
        "| Ticker | Company | From | To | Firm | New Price Target | After-Hours Reaction |",
        "|--------|---------|------|----|------|-----------------|---------------------|",
    ]
    L += analyst_rows(upgrades)
    L += ["", "### Downgrades",
        "| Ticker | Company | From | To | Firm | New Price Target | After-Hours Reaction |",
        "|--------|---------|------|----|------|-----------------|---------------------|",
    ]
    L += analyst_rows(downgrades)

    L += ["", "---", "",
        "## Economic Releases — Today's Results", "",
        "| Time (ET) | Event | Actual | Forecast | Previous | Beat / Miss | Market Reaction |",
        "|-----------|-------|--------|----------|----------|-------------|----------------|",
    ]
    L += econ_rows(econ_events, include_actual=True)

    L += ["", "---", "",
        "## Fed Watch", "",
        f"- **Today's Fed Activity:**",
        f"- **Current Fed Funds Rate:** {fed_val}",
        f"- **Rate Change Probability (CME FedWatch):**",
        f"- **Next FOMC Meeting:**",
        f"- **Notable Fed Speaker(s) Today:**",
        f"- **Key Quote:**",
    ]

    L += ["", "---", "",
        "## Sentiment Gauges", "",
        f"- **CNN Fear & Greed Index:** {fg_str}",
        "- **AAII Sentiment (latest weekly):** Bulls  % | Bears  % | Neutral  %",
        "- **Reading:**",
    ]

    L += ["", "---", "",
        "## Geopolitical & Macro Developments", "",
        "- **Global:**",
        "- **US:**",
        "- **Energy Markets:**",
        f"- **Currency (DXY):** {dxy_val}",
        f"- **Bond Market (10Y Yield):** {yield_val}",
    ]

    L += ["", "---", "",
        "## After-Hours Movers", "",
        "### After-Hours Gainers",
        "| Ticker | Company | % Change | Catalyst |",
        "|--------|---------|----------|---------|",
    ]
    L += mover_rows(ah_gainers)
    L += ["", "### After-Hours Losers",
        "| Ticker | Company | % Change | Catalyst |",
        "|--------|---------|----------|---------|",
    ]
    L += mover_rows(ah_losers)

    L += ["", "---", "",
        "## 1. Market Summary", "",
        "[Fill in]", "", "---", "",
        "## 2. Opportunities", "",
        "- ",
        "- ",
        "- ",
        "", "---", "",
        "## 3. Risks", "",
        "- ",
        "- ",
        "- ",
    ]

    L.append(DISCLAIMER)
    L.append(f"\n*File: `Close/Close_{fdate}.md` | Previous: `Open/Open_{fdate}.md`*")

    return "\n".join(L)

# ---------------------------------------------------------------------------
# Weekly report builder
# ---------------------------------------------------------------------------

def week_bounds(any_date_str):
    """Return (monday_str, friday_str) for the ISO week containing any_date_str."""
    d = datetime.strptime(any_date_str, "%Y-%m-%d")
    monday = d - timedelta(days=d.weekday())
    friday = monday + timedelta(days=4)
    return monday.strftime("%Y-%m-%d"), friday.strftime("%Y-%m-%d")


def build_weekly_report(week_date, raw_bars, macro_mon, macro_fri,
                        econ_week_events, upgrades, downgrades, fg_score, fg_label):
    monday_str, friday_str = week_bounds(week_date)
    monday = datetime.strptime(monday_str, "%Y-%m-%d")
    friday = datetime.strptime(friday_str, "%Y-%m-%d")
    week_dates = [(monday + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]

    fdate   = monday.strftime("%m-%d-%y")
    mon_str = monday.strftime("%B %-d")
    fri_str = friday.strftime("%B %-d, %Y")
    now_et  = datetime.now().strftime("%B %-d, %Y %I:%M %p")

    # Get Friday prices (for weekly table) and compute Mon open from bars
    fri_prices = compute_prices_for_date(raw_bars, friday_str)
    mon_prices = compute_prices_for_date(raw_bars, monday_str)

    y10  = macro_fri.get("10Y Yield")
    y2   = macro_fri.get("2Y Yield")
    fed  = macro_fri.get("Fed Funds Rate")
    dxy  = macro_fri.get("DXY")
    y10_mon = macro_mon.get("10Y Yield")
    y2_mon  = macro_mon.get("2Y Yield")
    spread_bps_fri = compute_spread(y10, y2)
    spread_bps_mon = compute_spread(y10_mon, y2_mon)

    fg_str = f"{fg_score} — {fg_label or fg_label_detail(fg_score)}" if fg_score else ""

    # Count trading days (skip weekends)
    trading_days = [d for d in week_dates
                    if datetime.strptime(d, "%Y-%m-%d").weekday() < 5]
    # Remove days with no data
    trading_days_with_data = [d for d in trading_days
                               if compute_prices_for_date(raw_bars, d).get("S&P 500", {}).get("close")]

    # Daily breakdown: day-over-day % for each index
    def daily_pcts_for_index(bars_key):
        bd = raw_bars.get(bars_key, {})
        pcts = []
        for d in week_dates:
            dobj = datetime.strptime(d, "%Y-%m-%d")
            if dobj.weekday() >= 5:
                pcts.append("")
                continue
            dates_sorted = sorted(bd.keys())
            before = [x for x in dates_sorted if x <= d]
            if len(before) < 2:
                pcts.append("")
                continue
            cur = bd[before[-1]]["c"]
            prev = bd[before[-2]]["c"]
            pcts.append(fmt_pct(pct(cur, prev)))
        return pcts

    # Best/worst ETF for week
    etf_weekly = {}
    for ticker in ETFS:
        mon_o = mon_prices.get(ticker, {}).get("open")
        fri_c = fri_prices.get(ticker, {}).get("close")
        if mon_o and fri_c:
            etf_weekly[ticker] = pct(fri_c, mon_o)
    best_etf = max(etf_weekly, key=etf_weekly.get) if etf_weekly else ""
    worst_etf = min(etf_weekly, key=etf_weekly.get) if etf_weekly else ""
    best_sector  = ETFS.get(best_etf, best_etf)
    worst_sector = ETFS.get(worst_etf, worst_etf)

    L = []
    L += [
        f"# Weekly Market Recap — Week of {mon_str} to {fri_str}",
        f"**Report Type:** Weekly",
        f"**Generated:** {now_et} ET",
        f"**Trading Days This Week:** {len(trading_days_with_data)}",
        "", "---", "",
        "## Major Indices — Week in Review", "",
        "| Index | Mon Open | Fri Close | Weekly % | Monthly % | 3 Month % | 6 Month % | YTD % |",
        "|-------|----------|-----------|----------|-----------|-----------|-----------|-------|",
    ]
    for name in INDICES:
        mon_o = mon_prices.get(name, {}).get("open")
        fri_c = fri_prices.get(name, {}).get("close")
        L.append(idx_row_weekly(name, mon_o, fri_c, fri_prices.get(name, {})))

    L += ["", "### Index Daily Breakdown",
        "| Index | Mon % | Tue % | Wed % | Thu % | Fri % | Weekly % |",
        "|-------|-------|-------|-------|-------|-------|----------|",
    ]
    for name, ticker in INDICES.items():
        pcts = daily_pcts_for_index(name)
        mon_o = mon_prices.get(name, {}).get("open")
        fri_c = fri_prices.get(name, {}).get("close")
        weekly = fmt_pct(pct(fri_c, mon_o)) if mon_o and fri_c else ""
        L.append(f"| {name} | {' | '.join(pcts)} | {weekly} |")

    L += ["", "---", "",
        "## Crypto — Week in Review", "",
        "| Asset | Mon Open | Fri Close | Weekly % | Monthly % | 3 Month % | 6 Month % | YTD % |",
        "|-------|----------|-----------|----------|-----------|-----------|-----------|-------|",
    ]
    for name in CRYPTO:
        mon_o = mon_prices.get(name, {}).get("open")
        fri_c = fri_prices.get(name, {}).get("close")
        L.append(asset_row_weekly(name, mon_o, fri_c, fri_prices.get(name, {})))

    L += ["", "---", "",
        "## Commodities — Week in Review", "",
        "| Asset | Mon Open | Fri Close | Weekly % | Monthly % | 3 Month % | 6 Month % | YTD % |",
        "|-------|----------|-----------|----------|-----------|-----------|-----------|-------|",
    ]
    for name in list(COMMODITIES_POLY) + list(COMMODITIES_YF):
        mon_o = mon_prices.get(name, {}).get("open")
        fri_c = fri_prices.get(name, {}).get("close")
        L.append(asset_row_weekly(name, mon_o, fri_c, fri_prices.get(name, {})))

    L += ["", "---", "",
        "## Sector Performance — Week", "",
        "| Sector | ETF | Mon Open | Fri Close | Weekly % | Monthly % | 3 Month % | 6 Month % | Relative to S&P |",
        "|--------|-----|----------|-----------|----------|-----------|-----------|-----------|----------------|",
    ]
    for ticker in ETFS:
        mon_o = mon_prices.get(ticker, {}).get("open")
        fri_c = fri_prices.get(ticker, {}).get("close")
        L.append(etf_row_weekly(ticker, mon_o, fri_c, fri_prices.get(ticker, {})))
    L += [
        "",
        f"**Best sector this week:** {best_sector} ({best_etf}) {fmt_pct(etf_weekly.get(best_etf))}",
        f"**Worst sector this week:** {worst_sector} ({worst_etf}) {fmt_pct(etf_weekly.get(worst_etf))}",
        "**Sector rotation narrative:**",
    ]

    vix_fri  = fri_prices.get("VIX", {})
    vix9_fri = fri_prices.get("VIX9D", {})
    vix_mon  = mon_prices.get("VIX", {})
    vix9_mon = mon_prices.get("VIX9D", {})
    vix_fri_val  = vix_fri.get("close")
    vix9_fri_val = vix9_fri.get("close")
    vix_mon_val  = vix_mon.get("open")
    vix9_mon_val = vix9_mon.get("open")

    L += ["", "---", "",
        "## Volatility & Options — Weekly", "",
        "| Indicator | Mon Open | Fri Close | Weekly Chg | Week High | Week Low |",
        "|-----------|----------|-----------|------------|-----------|---------|",
        f"| VIX (30-day) | {fmt_price(vix_mon_val)} | {fmt_price(vix_fri_val)} | {fmt_pct(pct(vix_fri_val, vix_mon_val)) if vix_fri_val and vix_mon_val else ''} | | |",
        f"| VIX9D (9-day) | {fmt_price(vix9_mon_val)} | {fmt_price(vix9_fri_val)} | {fmt_pct(pct(vix9_fri_val, vix9_mon_val)) if vix9_fri_val and vix9_mon_val else ''} | | |",
        "",
        "**Put/Call ratio trend this week:**",
        "**Volatility interpretation:**",
    ]

    L += ["", "---", "",
        "## Market Breadth — Friday Snapshot", "",
        "| Indicator | Value | Signal |",
        "|-----------|-------|--------|",
        "| NYSE Advance / Decline | / | |",
        "| S&P 500 Above 50-Day MA | % | Healthy > 60% |",
        "| S&P 500 Above 200-Day MA | % | Bull market > 70% |",
        "| NYSE New 52-Week Highs | | |",
        "| NYSE New 52-Week Lows | | |",
        "| Nasdaq New 52-Week Highs | | |",
        "| Nasdaq New 52-Week Lows | | |",
    ]

    hyg_fri = fri_prices.get("HYG", {})
    lqd_fri = fri_prices.get("LQD", {})
    hyg_mon = mon_prices.get("HYG", {})
    lqd_mon = mon_prices.get("LQD", {})
    y10_val = f"{y10:.2f}%" if y10 else ""
    y2_val  = f"{y2:.2f}%" if y2 else ""
    y10_mon_val = f"{y10_mon:.2f}%" if y10_mon else ""
    y2_mon_val  = f"{y2_mon:.2f}%" if y2_mon else ""
    spread_fri_str = f"{spread_bps_fri:+d} bps" if spread_bps_fri is not None else ""
    spread_mon_str = f"{spread_bps_mon:+d} bps" if spread_bps_mon is not None else ""
    spread_chg = ""
    if spread_bps_fri is not None and spread_bps_mon is not None:
        spread_chg = f"{spread_bps_fri - spread_bps_mon:+d} bps"

    L += ["", "---", "",
        "## Yield Curve & Credit — Weekly", "",
        "| Indicator | Mon Open | Fri Close | Weekly Chg | Signal |",
        "|-----------|----------|-----------|------------|--------|",
        f"| 2-Year Treasury Yield | {y2_mon_val} | {y2_val} | bps | Fed-sensitive |",
        f"| 10-Year Treasury Yield | {y10_mon_val} | {y10_val} | bps | Growth / inflation |",
        f"| 2Y / 10Y Spread | {spread_mon_str} | {spread_fri_str} | {spread_chg} | {spread_signal(spread_bps_fri)} |",
        f"| HYG (High Yield) | {fmt_price(hyg_mon.get('open'))} | {fmt_price(hyg_fri.get('close'))} | {fmt_pct(pct(hyg_fri.get('close'), hyg_mon.get('open')))} | Risk appetite |",
        f"| LQD (Inv. Grade) | {fmt_price(lqd_mon.get('open'))} | {fmt_price(lqd_fri.get('close'))} | {fmt_pct(pct(lqd_fri.get('close'), lqd_mon.get('open')))} | Credit quality |",
    ]

    L += ["", "---", "",
        "## Top Gainers of the Week (S&P 500)", "",
        "| Rank | Ticker | Company | Sector | Weekly % | Catalyst |",
        "|------|--------|---------|--------|----------|---------|",
        "| 1 | | | | | |",
        "| 2 | | | | | |",
        "| 3 | | | | | |",
        "| 4 | | | | | |",
        "| 5 | | | | | |",
    ]

    L += ["", "---", "",
        "## Top Losers of the Week (S&P 500)", "",
        "| Rank | Ticker | Company | Sector | Weekly % | Catalyst |",
        "|------|--------|---------|--------|----------|---------|",
        "| 1 | | | | | |",
        "| 2 | | | | | |",
        "| 3 | | | | | |",
        "| 4 | | | | | |",
        "| 5 | | | | | |",
    ]

    L += ["", "---", "",
        "## Analyst Actions — Week in Review", "",
        "### Notable Upgrades",
        "| Ticker | Company | From | To | Firm | Price Target | Week % After |",
        "|--------|---------|------|----|------|-------------|-------------|",
    ]
    if upgrades:
        for x in upgrades:
            L.append(f"| {x['ticker']} | {x['company']} | {x['from']} | {x['to']} | {x['firm']} | {x['target']} | |")
    else:
        L += ["| | | | | | | |", "| | | | | | | |"]

    L += ["", "### Notable Downgrades",
        "| Ticker | Company | From | To | Firm | Price Target | Week % After |",
        "|--------|---------|------|----|------|-------------|-------------|",
    ]
    if downgrades:
        for x in downgrades:
            L.append(f"| {x['ticker']} | {x['company']} | {x['from']} | {x['to']} | {x['firm']} | {x['target']} | |")
    else:
        L += ["| | | | | | | |", "| | | | | | | |"]

    # Economic calendar for the week
    L += ["", "---", "",
        "## Economic Releases — This Week", "",
        "| Day | Event | Actual | Forecast | Previous | Beat / Miss | Market Reaction |",
        "|-----|-------|--------|----------|----------|-------------|----------------|",
    ]
    if econ_week_events:
        for day_str, day_events in econ_week_events:
            day_label = datetime.strptime(day_str, "%Y-%m-%d").strftime("%a")
            for e in day_events:
                actual = e.get("actual", "")
                est = e.get("forecast", "")
                prev = e.get("previous", "")
                beat_miss = ""
                if actual and est:
                    try:
                        a = float(actual.replace("%","").replace("K","000").replace("M","000000"))
                        f = float(est.replace("%","").replace("K","000").replace("M","000000"))
                        beat_miss = "Beat" if a > f else ("Miss" if a < f else "In Line")
                    except Exception:
                        pass
                L.append(f"| {day_label} | {e.get('event','')} | {actual} | {est} | {prev} | {beat_miss} | |")
    else:
        for day_label in day_names:
            L.append(f"| {day_label} | | | | | | |")

    fed_val = f"{fed:.2f}%" if fed else ""

    L += [
        "",
        "**Most market-moving release this week:**",
        "**Data trend summary:**",
    ]

    L += ["", "---", "",
        "## Fed Watch — Weekly", "",
        "- **FOMC Activity This Week:**",
        f"- **Current Fed Funds Rate:** {fed_val}",
        "- **Fed Speakers This Week:**",
        "- **Key Quotes:**",
        "- **Rate Change Probability (CME FedWatch):**",
        "- **Next FOMC Meeting:**",
        "- **Fed Narrative Shift This Week (if any):**",
    ]

    L += ["", "---", "",
        "## Sentiment Gauges — Weekly", "",
        f"- **CNN Fear & Greed Index (Friday):** {fg_str} | Weekly trend: Rising / Falling / Stable",
        "- **AAII Sentiment (latest weekly):** Bulls  % | Bears  % | Neutral  %",
        "- **Reading:**",
    ]

    L += ["", "---", "",
        "## Geopolitical & Macro — Week in Review", "",
        "- **Global:**",
        "- **US Policy / Politics:**",
        "- **Energy Markets:**",
        f"- **Currency (DXY weekly %):**",
        f"- **Bond Market (10Y Yield — start / end / change):** {y10_mon_val} / {y10_val} / ",
        "- **Credit Markets (HYG, LQD):**",
    ]

    L += ["", "---", "",
        "## Next Week — Economic Calendar Preview", "",
        "| Day | Event | Forecast | Previous | Importance |",
        "|-----|-------|----------|----------|------------|",
        "| Mon | | | | High / Med / Low |",
        "| Tue | | | | |",
        "| Wed | | | | |",
        "| Thu | | | | |",
        "| Fri | | | | |",
        "",
        "**Key earnings next week:**",
        "**Key Fed speakers next week:**",
    ]

    L += ["", "---", "",
        "## 1. Market Summary", "",
        "[Fill in]", "", "---", "",
        "## 2. Opportunities", "",
        "- ",
        "- ",
        "- ",
        "", "---", "",
        "## 3. Risks", "",
        "- ",
        "- ",
        "- ",
    ]

    L.append(DISCLAIMER)
    L.append(f"\n*File: `Weekly/Weekly_{fdate}.md`*")

    return "\n".join(L)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TRADING_DAYS_2026_JUN = [
    # June 2026 — Juneteenth (6/19) is a federal holiday
    "2026-06-01","2026-06-02","2026-06-03","2026-06-04","2026-06-05",
    "2026-06-08","2026-06-09","2026-06-10","2026-06-11","2026-06-12",
    "2026-06-15","2026-06-16","2026-06-17","2026-06-18",
    "2026-06-22","2026-06-23","2026-06-24","2026-06-25","2026-06-26",
]

def is_trading_day(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    if d.weekday() >= 5:
        return False
    # Juneteenth 2026
    if date_str == "2026-06-19":
        return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None)
    parser.add_argument("--dates", nargs="+", default=None)
    parser.add_argument("--type", choices=["open", "close", "both", "weekly", "all"],
                        default="both")
    args = parser.parse_args()

    if args.dates:
        dates = sorted([d for d in args.dates if is_trading_day(d)])
    else:
        d = args.date or datetime.now().strftime("%Y-%m-%d")
        dates = [d]

    report_type = args.type

    print(f"\n=== GlobalMarkets Investor Report Generator ===")
    print(f"Dates: {', '.join(dates)}")
    print(f"Type : {report_type}")
    print(f"APIs : Polygon={'✓' if POLYGON_KEY else '✗'}  "
          f"AV={'✓' if AV_KEY else '✗'}  "
          f"Finnhub={'✓' if FINNHUB_KEY else '✗'}  "
          f"FMP={'✓' if FMP_KEY else '✗'}  "
          f"FRED={'✓' if FRED_KEY else '✗'}\n")

    # Fear & Greed (current — best we can do for historical is current value)
    fg_score, fg_label = fetch_fear_greed()

    # Gainers/losers and movers (current day, real-time only)
    gainers, losers = fetch_gainers_losers()
    pre_g, pre_l = ([], [])
    ah_g, ah_l   = ([], [])
    if report_type in ("open", "both", "all"):
        pre_g, pre_l = fetch_premarket_movers()
    if report_type in ("close", "both", "all"):
        ah_g, ah_l = fetch_afterhours_movers()

    if len(dates) > 1 or report_type in ("weekly", "all"):
        # Batch: fetch bars once
        lookback_start = (datetime.strptime(dates[0], "%Y-%m-%d") - timedelta(days=260)).strftime("%Y-%m-%d")
        end_date = dates[-1]
        raw_bars = fetch_bars_all(lookback_start, end_date)
        get_prices = lambda d: compute_prices_for_date(raw_bars, d)
    else:
        raw_bars = None
        get_prices = lambda d: fetch_prices(d)

    # Economic calendar cache is per-session (current week only from FF)
    # For dates (generate Open/Close)
    if report_type in ("open", "close", "both", "all"):
        for report_date in dates:
            if not is_trading_day(report_date):
                print(f"  Skipping {report_date} (non-trading day)")
                continue

            fdate    = datetime.strptime(report_date, "%Y-%m-%d").strftime("%m-%d-%y")
            day_name = datetime.strptime(report_date, "%Y-%m-%d").strftime("%A")
            print(f"\n--- {report_date} ({day_name}) ---")

            prices  = get_prices(report_date)
            macro   = fetch_fred(report_date)
            upgr, downgr = fetch_analyst_actions(report_date)
            econ    = fetch_economic_calendar(report_date)

            if report_type in ("open", "both", "all"):
                content = build_open_report(report_date, prices, macro,
                                            pre_g, pre_l, upgr, downgr, econ,
                                            fg_score, fg_label)
                out = REPORTS_DIR / "Open" / f"Open_{fdate}.md"
                out.write_text(content)
                print(f"  ✓ Open  → {out}")

            if report_type in ("close", "both", "all"):
                content = build_close_report(report_date, prices, macro,
                                             gainers, losers, ah_g, ah_l,
                                             upgr, downgr, econ, fg_score, fg_label)
                out = REPORTS_DIR / "Close" / f"Close_{fdate}.md"
                out.write_text(content)
                print(f"  ✓ Close → {out}")

    # Weekly reports
    if report_type in ("weekly", "all"):
        # Find unique week Mondays covered by dates
        weeks_seen = set()
        for d in dates:
            monday, _ = week_bounds(d)
            weeks_seen.add(monday)

        for monday_str in sorted(weeks_seen):
            friday_str = (datetime.strptime(monday_str, "%Y-%m-%d") + timedelta(days=4)).strftime("%Y-%m-%d")
            print(f"\n--- Weekly: {monday_str} → {friday_str} ---")

            # Collect econ events for the whole week
            week_dates = [(datetime.strptime(monday_str, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
                          for i in range(5)]
            econ_week = [(d, fetch_economic_calendar(d)) for d in week_dates
                         if is_trading_day(d)]

            macro_mon = fetch_fred(monday_str)
            macro_fri = fetch_fred(friday_str)
            upgr, downgr = fetch_analyst_actions(friday_str)

            if raw_bars is None:
                raw_bars = fetch_bars_all(
                    (datetime.strptime(monday_str, "%Y-%m-%d") - timedelta(days=260)).strftime("%Y-%m-%d"),
                    friday_str
                )

            content = build_weekly_report(
                monday_str, raw_bars, macro_mon, macro_fri,
                econ_week, upgr, downgr, fg_score, fg_label
            )
            fdate = datetime.strptime(monday_str, "%Y-%m-%d").strftime("%m-%d-%y")
            out = REPORTS_DIR / "Weekly" / f"Weekly_{fdate}.md"
            out.write_text(content)
            print(f"  ✓ Weekly → {out}")

    print("\nDone. Manual sections to complete: Market Tone, Market Summary, Opportunities,")
    print("Risks, Key Levels, Market Breadth, Put/Call Ratio, Fed Watch details,")
    print("Geopolitical/Macro, Earnings Calendar, AAII Sentiment, Weekly Top Gainers/Losers.")


if __name__ == "__main__":
    main()
