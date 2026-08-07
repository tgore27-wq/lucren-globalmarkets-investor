# Market Breadth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blank "Market Breadth" table (Advance/Decline, %>50/200-day MA, 52-week highs/lows) and the blank "Top Gainers/Losers of the Week" tables in all three report types with real numbers computed in-house from free, bulk-downloaded S&P 500 price data — no new paid subscription.

**Architecture:** A new `market_breadth.py` module owns: (1) a locally-cached S&P 500 constituent list scraped from Wikipedia, (2) one bulk `yfinance` download of ~1 year of daily bars for the whole universe, (3) pure-Python aggregation into breadth stats and weekly top movers. `generate_report.py` calls this once per report run (not once per report *type* — Open/Close share a date, so they share one breadth fetch) and formats the result with a shared table-builder helper reused by `build_open_report`, `build_close_report`, and `build_weekly_report`.

**Tech Stack:** `yfinance` (bulk multi-ticker download, already a dependency), `pandas` (already a dependency, used for HTML table parsing + aggregation), `requests` (already a dependency, for the Wikipedia fetch).

## Global Constraints

- Polygon is NOT viable for this: its free-tier rate limit is 5 calls/minute (see `_poly_rate_limit()` in `generate_report.py:143`), and a 503-ticker universe at 1 call/ticker would take ~100 minutes. `yf.download()` batches many tickers into one threaded call — measured at 8.1s for 100 tickers/1yr live against this exact environment, so ~500 tickers should land well under a minute.
- The S&P 500 mixes NYSE- and Nasdaq-listed names; we do not have a clean per-exchange split. **Do not label anything "NYSE ..." or "Nasdaq ..."** — that would misrepresent the data source. All breadth rows must be labeled "S&P 500 ..." instead. This is a rename, not a placeholder — apply it everywhere the old labels appear.
- Every new fetch function must never raise out of `fetch_market_breadth()` — on any failure it returns `None`, and callers must render the existing "Data not available" fallback, exactly like every other fetcher in this codebase (see `fetch_premarket_movers()` in `generate_report.py:474` for the pattern).
- No test framework exists in this repo (verified: no `tests/`, no `pytest.ini`, no `conftest.py`). Do not add one. "Test" steps in this plan are direct script invocations with printed/inspected output, matching how `fetch_earnings_calendar` was verified (`python3 -c "import generate_report as gr; ..."`) and how the repo's own `cron_selftest.sh` works.
- **Never run `generate_report.py` (or `run_report.sh`) against today's date or any already-committed past date while testing** — it overwrites the real report file in place. This bit us once already this week (a test run clobbered `Open/Open_08-06-26.md`, recovered via `git checkout`). Use an explicit past scratch date that has never been generated (pick one outside the existing `Open/`/`Close/` directory listing) or call the new functions directly via `python3 -c`, never the full `main()`.

---

### Task 1: S&P 500 universe fetch with local caching

**Files:**
- Create: `market_breadth.py`
- Modify: `.gitignore` (add cache file)

**Interfaces:**
- Produces: `get_sp500_universe() -> list[dict]`, each dict `{"ticker": str, "company": str, "sector": str}`. Tickers have `.` replaced with `-` (yfinance's format, e.g. `BRK.B` → `BRK-B`).

- [ ] **Step 1: Create `market_breadth.py` with the universe fetcher**

```python
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
```

- [ ] **Step 2: Add the cache file to `.gitignore`**

Add this line under the existing "Private local PDFs" block in `.gitignore`:

```
sp500_universe_cache.json
```

- [ ] **Step 3: Verify it fetches real data**

Run: `/usr/local/bin/python3 -c "import market_breadth as mb; u = mb.get_sp500_universe(); print(len(u)); print(u[0]); print(u[-1])"`

Expected: prints a number close to 500 (S&P 500 constituent count fluctuates slightly), then a first and last dict each shaped like `{"ticker": "MMM", "company": "3M", "sector": "Industrials"}`.

- [ ] **Step 4: Verify the cache was written and is reused**

Run: `ls -la sp500_universe_cache.json && /usr/local/bin/python3 -c "import time; import market_breadth as mb; t0=time.time(); mb.get_sp500_universe(); print('cached read:', round(time.time()-t0,2), 's')"`

Expected: file exists; the second run prints well under 1s (no network call — compare against the multi-second Wikipedia fetch in Step 3).

- [ ] **Step 5: Commit**

```bash
git add market_breadth.py .gitignore
git commit -m "Add S&P 500 universe fetcher with local cache for market breadth"
```

---

### Task 2: Bulk price download + breadth/movers computation

**Files:**
- Modify: `market_breadth.py`

**Interfaces:**
- Consumes: `get_sp500_universe() -> list[dict]` (Task 1)
- Produces: `fetch_market_breadth(as_of_date: str) -> dict | None`, where the dict (when not None) has keys: `advances`, `declines`, `pct_above_50dma`, `pct_above_200dma`, `new_52wk_highs`, `new_52wk_lows`, `universe_size`, `top_gainers`, `top_losers`. `top_gainers`/`top_losers` are each `list[tuple[float, str, str, str]]` of `(pct_change, ticker, company, sector)`, sorted best-first, capped at 5.

- [ ] **Step 1: Append the bars downloader, breadth computation, and top-level entry point to `market_breadth.py`**

```python
from datetime import datetime


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


def compute_breadth(bars, universe, as_of_date):
    """Compute breadth stats using the most recent trading day on or
    before as_of_date present in bars (bars can lag by a day if run
    before Yahoo prints the latest close). Returns a dict, or None if
    bars is unusable."""
    if bars is None or bars.empty or not isinstance(bars.columns, pd.MultiIndex):
        return None

    target = pd.Timestamp(as_of_date)
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

        info = by_ticker.get(ticker, {})
        movers.append(((last / prev - 1) * 100, ticker,
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


def fetch_market_breadth(as_of_date):
    """Top-level entry point: universe -> bulk bars -> stats. Never
    raises — returns None on any failure so callers fall back to
    'Data not available', same convention as every other fetcher in
    this pipeline (see fetch_premarket_movers in generate_report.py)."""
    print("Fetching market breadth (S&P 500, yfinance bulk)...")
    try:
        universe = get_sp500_universe()
        bars = fetch_breadth_bars(universe)
        result = compute_breadth(bars, universe, as_of_date)
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
```

- [ ] **Step 2: Verify against a known recent trading day**

Run: `/usr/local/bin/python3 -c "
import market_breadth as mb
r = mb.fetch_market_breadth('2026-08-05')
import json; print(json.dumps(r, indent=2, default=str))
"`

Expected: takes roughly 30-90s (first run re-downloads bars; the universe list itself should hit the Task 1 cache). Prints a dict with `advances`/`declines` summing to at most `universe_size` (some tickers can be flat), `pct_above_50dma`/`pct_above_200dma` between 0-100, and `top_gainers`/`top_losers` each 5 tuples with plausible daily % moves (single digits, not e.g. 500%).

- [ ] **Step 3: Sanity-check one ticker by hand**

Run: `/usr/local/bin/python3 -c "
import yfinance as yf
d = yf.download('AAPL', period='5d', progress=False)
print(d['Close'].tail(2))
"`
Compare AAPL's computed daily % change against what `compute_breadth` would derive for AAPL on the same date (it should appear in `top_gainers`/`top_losers` only if it's a top-5 mover — if not, manually verify the sign/rough magnitude matches by checking `Open/Open_08-05-26.md`'s "Major Indices" data doesn't contradict a broad market direction implied by advances vs. declines, e.g. don't expect 480 advances on a day the report already shows major indices down).

- [ ] **Step 4: Commit**

```bash
git add market_breadth.py
git commit -m "Add bulk breadth computation (advance/decline, MA%, 52wk hi/lo, weekly movers)"
```

---

### Task 3: Shared table-formatting helper + wire into Open and Close reports

**Files:**
- Modify: `generate_report.py:1-40` (add `import market_breadth` near the other imports)
- Modify: `generate_report.py` (add helper function near other `fmt_*` helpers)
- Modify: `generate_report.py:1121-1132` (Open report's blank Market Breadth block)
- Modify: `generate_report.py:1340-1351` (Close report's blank Market Breadth block)
- Modify: `build_open_report()` signature — add `breadth=None` parameter
- Modify: `build_close_report()` signature — add `breadth=None` parameter

**Interfaces:**
- Consumes: `fetch_market_breadth(as_of_date) -> dict | None` (Task 2)
- Produces: `format_breadth_table(breadth, header="## Market Breadth") -> list[str]` — reused by Task 3 (Open/Close) and Task 4 (Weekly).

- [ ] **Step 1: Add the import**

In `generate_report.py`, near the top where `import yfinance as yf` already lives (around line 34), add:

```python
import market_breadth
```

- [ ] **Step 2: Add the shared table-formatting helper**

Find where other small formatting helpers live (e.g. `fmt_price`, `fmt_pct` — search `def fmt_price`) and add nearby:

```python
def format_breadth_table(breadth, header="## Market Breadth"):
    """Shared by Open, Close, and Weekly builders. breadth is the dict
    from market_breadth.fetch_market_breadth(), or None. Labeled
    'S&P 500 ...' throughout — NOT 'NYSE'/'Nasdaq', since the universe
    is the S&P 500 constituent list, which spans both exchanges."""
    lines = ["", "---", "", header, "",
             "| Indicator | Value | Signal |",
             "|-----------|-------|--------|"]
    if not breadth:
        lines += [
            "| S&P 500 Advance / Decline | — / — | *Data not available* |",
            "| S&P 500 Above 50-Day MA | — % | *Data not available* |",
            "| S&P 500 Above 200-Day MA | — % | *Data not available* |",
            "| S&P 500 New 52-Week Highs | — | *Data not available* |",
            "| S&P 500 New 52-Week Lows | — | *Data not available* |",
        ]
        return lines
    adv, decl = breadth["advances"], breadth["declines"]
    signal = "Breadth bullish" if adv > decl else ("Breadth bearish" if decl > adv else "Breadth flat")
    ma50, ma200 = breadth["pct_above_50dma"], breadth["pct_above_200dma"]
    lines += [
        f"| S&P 500 Advance / Decline | {adv} / {decl} | {signal} |",
        f"| S&P 500 Above 50-Day MA | {ma50}% | {'Healthy' if ma50 > 60 else 'Weak'} (> 60% healthy) |",
        f"| S&P 500 Above 200-Day MA | {ma200}% | {'Bull market' if ma200 > 70 else 'Below bull threshold'} (> 70%) |",
        f"| S&P 500 New 52-Week Highs | {breadth['new_52wk_highs']} | |",
        f"| S&P 500 New 52-Week Lows | {breadth['new_52wk_lows']} | |",
    ]
    return lines
```

- [ ] **Step 3: Wire into `build_open_report`**

Change the signature (currently `def build_open_report(report_date, prices, macro, pre_gainers, pre_losers, upgrades, downgrades, econ_events, fg_score, fg_label, earnings=None):`) to also accept `breadth=None`:

```python
def build_open_report(report_date, prices, macro, pre_gainers, pre_losers,
                      upgrades, downgrades, econ_events, fg_score, fg_label,
                      earnings=None, breadth=None):
```

Replace the existing blank block:
```python
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
```
with:
```python
    L += format_breadth_table(breadth)
```

- [ ] **Step 4: Wire into `build_close_report`** — same pattern

Add `breadth=None` to `build_close_report`'s signature, and replace its identical blank block (currently at `generate_report.py:1340-1351`, header `"## Market Breadth"`, same 7 rows) with `L += format_breadth_table(breadth)`.

- [ ] **Step 5: Verify formatting in isolation (no live report file touched)**

Run: `/usr/local/bin/python3 -c "
import generate_report as gr
fake = {'advances': 310, 'declines': 190, 'pct_above_50dma': 62.4,
        'pct_above_200dma': 71.8, 'new_52wk_highs': 24, 'new_52wk_lows': 6,
        'universe_size': 500, 'top_gainers': [], 'top_losers': []}
print('\n'.join(gr.format_breadth_table(fake)))
print('---None case---')
print('\n'.join(gr.format_breadth_table(None)))
"`

Expected: first block shows real numbers with "S&P 500" labels and correct bullish/healthy/bull-market signal words; second block shows all five rows as "*Data not available*" with no exceptions raised.

- [ ] **Step 6: Verify end-to-end against a scratch date (never a real report date)**

Run: `/usr/local/bin/python3 -c "
import generate_report as gr
import market_breadth as mb
breadth = mb.fetch_market_breadth('2026-08-05')
content = gr.build_open_report('2026-08-05', {}, {}, [], [], [], [], [], None, '', breadth=breadth)
print([l for l in content.split(chr(10)) if 'S&P 500 Advance' in l or 'S&P 500 Above' in l])
" `

Expected: prints the populated Advance/Decline and MA% lines with real numbers — this calls `build_open_report` directly (not `main()`, not `generate_report.py`'s CLI), so **no file on disk is touched**, satisfying the Global Constraint above.

- [ ] **Step 7: Commit**

```bash
git add generate_report.py
git commit -m "Wire real Market Breadth data into Open and Close reports"
```

---

### Task 4: Wire into Weekly report + Top Gainers/Losers of the Week

**Files:**
- Modify: `generate_report.py:1618-1628` (Weekly's blank Market Breadth block)
- Modify: `generate_report.py:1656-1675` (Weekly's blank Top Gainers/Losers blocks)
- Modify: `build_weekly_report()` signature — add `breadth=None` parameter

**Interfaces:**
- Consumes: `format_breadth_table()` (Task 3), the `top_gainers`/`top_losers` fields from `fetch_market_breadth()`'s return dict (Task 2)

- [ ] **Step 1: Wire the breadth table**

Add `breadth=None` to `build_weekly_report`'s signature (currently `def build_weekly_report(week_date, raw_bars, macro_mon, macro_fri, econ_week_events, upgrades, downgrades, fg_score, fg_label):`):

```python
def build_weekly_report(week_date, raw_bars, macro_mon, macro_fri,
                        econ_week_events, upgrades, downgrades, fg_score, fg_label,
                        breadth=None):
```

Replace the existing blank block (header `"## Market Breadth — Friday Snapshot"`, same 7 rows as Open/Close) with:

```python
    L += format_breadth_table(breadth, header="## Market Breadth — Friday Snapshot")
```

- [ ] **Step 2: Add a weekly-movers formatting helper next to `format_breadth_table`**

```python
def format_weekly_movers_table(movers, title):
    """movers: list of (pct_change, ticker, company, sector) tuples,
    best-first for gainers / worst-first for losers, from
    market_breadth.fetch_market_breadth()'s top_gainers/top_losers."""
    lines = ["", "---", "", title, "",
             "| Rank | Ticker | Company | Sector | Weekly % | Catalyst |",
             "|------|--------|---------|--------|----------|---------|"]
    if not movers:
        lines.append("| — | — | *Data not available — weekly per-company movers* | — | — | — |")
        return lines
    for i, (pct_chg, ticker, company, sector) in enumerate(movers, 1):
        lines.append(f"| {i} | {ticker} | {company} | {sector} | {pct_chg:+.1f}% | — |")
    return lines
```

Note: this reuses the *daily* (not weekly) `top_gainers`/`top_losers` `compute_breadth()` already computes as of Friday — that's a same-day mover, not a true week-over-week mover, and the table is titled "Weekly %". This is a known limitation, not a silent inaccuracy: flag it to your human partner before Step 4 rather than shipping a mislabeled column. (See "Known limitation" note at the end of this task.)

- [ ] **Step 3: Wire the two weekly-movers tables**

Replace the existing blank block:
```python
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
```
with:
```python
    L += format_weekly_movers_table(
        breadth.get("top_gainers") if breadth else None,
        "## Top Gainers of the Week (S&P 500)")
    L += format_weekly_movers_table(
        breadth.get("top_losers") if breadth else None,
        "## Top Losers of the Week (S&P 500)")
```

- [ ] **Step 4: STOP — resolve the known limitation before committing**

`compute_breadth()` as built in Task 2 computes **daily** (last close vs. prior close) movers, but this table is titled "Weekly %" and headed "Top Gainers/Losers **of the Week**". Ship this task with one of these two fixes, not the mismatched version:

- **Fix A (recommended, small change):** in `compute_breadth()`, when `as_of_date` is a Friday (weekly report path), compute `pct_change` as `(friday_close / monday_open - 1) * 100` instead of `(last/prev - 1)*100` for the mover ranking only (advances/declines/MA%/52wk logic stays daily-vs-prior-day, that part is correct as-is). Add an `as_of_date` week-start lookup: `monday = target - pd.Timedelta(days=target.dayofweek)`, find the first close `>= monday` in `closes`, use that as the week-open reference instead of `prev`.
- **Fix B (simpler, if Fix A's date math proves fiddly):** rename the table headers to "Top Gainers/Losers — Friday Session (S&P 500)" and the column to "Daily %" instead of "Weekly %", so the label matches what's actually computed. Less ideal but honest, and ships today.

Pick one, implement it, and only then proceed to Step 5. Do not ship the mismatch silently.

- [ ] **Step 5: Verify weekly wiring in isolation**

Run: `/usr/local/bin/python3 -c "
import generate_report as gr
import market_breadth as mb
breadth = mb.fetch_market_breadth('2026-08-07')
content = gr.build_weekly_report('2026-08-03', None, {}, {}, [], [], [], None, '', breadth=breadth)
lines = content.split(chr(10))
print('\n'.join(l for l in lines if 'S&P 500' in l or l.startswith('| 1 |') or l.startswith('| 2 |')))
"`

Expected: breadth rows populated, and both movers tables show 5 real ranked rows (ticker/company/sector/% filled, Catalyst column "—"). This calls `build_weekly_report` directly — no file written.

- [ ] **Step 6: Commit**

```bash
git add generate_report.py
git commit -m "Wire real Market Breadth + weekly top movers into Weekly report"
```

---

### Task 5: Wire the fetch into `main()` — once per date, shared by Open/Close

**Files:**
- Modify: `generate_report.py` (inside `main()`, the per-date loop around `generate_report.py:1864-1892`, and the weekly loop around `generate_report.py:1925-1928`)

**Interfaces:**
- Consumes: `market_breadth.fetch_market_breadth()` (Task 2), `build_open_report(..., breadth=...)`, `build_close_report(..., breadth=...)`, `build_weekly_report(..., breadth=...)` (Tasks 3-4)

- [ ] **Step 1: Fetch once per report_date in the daily loop**

In `main()`, find:
```python
            prices  = get_prices(report_date)
            macro   = fetch_fred(report_date)
            upgr, downgr = fetch_analyst_actions(report_date)
            econ    = fetch_economic_calendar(report_date)
```
Add one line after it:
```python
            breadth = market_breadth.fetch_market_breadth(report_date)
```

- [ ] **Step 2: Pass it into both builders**

Find:
```python
            if report_type in ("open", "both", "all"):
                earn = fetch_earnings_calendar(report_date)
                content = build_open_report(report_date, prices, macro,
                                            pre_g, pre_l, upgr, downgr, econ,
                                            fg_score, fg_label, earnings=earn)
```
Change the last line to:
```python
                content = build_open_report(report_date, prices, macro,
                                            pre_g, pre_l, upgr, downgr, econ,
                                            fg_score, fg_label, earnings=earn,
                                            breadth=breadth)
```

Find:
```python
            if report_type in ("close", "both", "all"):
                content = build_close_report(report_date, prices, macro,
                                             gainers, losers, ah_g, ah_l,
                                             upgr, downgr, econ, fg_score, fg_label)
```
Change to:
```python
            if report_type in ("close", "both", "all"):
                content = build_close_report(report_date, prices, macro,
                                             gainers, losers, ah_g, ah_l,
                                             upgr, downgr, econ, fg_score, fg_label,
                                             breadth=breadth)
```

- [ ] **Step 3: Fetch once per week in the weekly loop**

Find:
```python
            content = build_weekly_report(
                monday_str, raw_bars, macro_mon, macro_fri,
                econ_week, upgr, downgr, fg_score, fg_label
            )
```
Change to:
```python
            week_breadth = market_breadth.fetch_market_breadth(friday_str)
            content = build_weekly_report(
                monday_str, raw_bars, macro_mon, macro_fri,
                econ_week, upgr, downgr, fg_score, fg_label,
                breadth=week_breadth
            )
```

- [ ] **Step 4: Full dry-run against a scratch date — confirm one fetch, not three**

Run: `/usr/local/bin/python3 generate_report.py --type open --date 2020-01-02 2>&1 | grep -c "Fetching market breadth"`

Expected: `1`. January 2, 2020 is a real trading day far outside this repo's `Open/`/`Close/` directories (confirm first with `ls Open/ | grep 01-02-20` — should be empty), so this is safe to run via the full CLI without risking a real report file. **Delete the generated file afterward** (`rm -f Open/Open_01-02-20.md`) since it's scratch output, not a real report.

- [ ] **Step 5: Commit**

```bash
git add generate_report.py
git commit -m "Fetch market breadth once per report date, shared across Open/Close/Weekly"
```

---

### Task 6: Anti-fabrication instructions for the new tables

**Files:**
- Modify: `fill_narratives.py` (system prompt, near instruction 11 which was already updated for Earnings Calendar)

**Interfaces:**
- None (prompt text only)

- [ ] **Step 1: Add a rule alongside the existing Earnings Calendar carve-out**

Find the instruction block updated for earnings calendar (search `Earnings Calendar: this table is pre-filled`) and add immediately after it:

```python
12. Market Breadth and Top Gainers/Losers of the Week: also pre-filled
    with real data (S&P 500, computed from yfinance). Leave every row
    exactly as written — same rule as Earnings Calendar and Analyst
    Actions (CRITICAL rule A): never invent a Catalyst to replace a "—"
    placeholder in the weekly movers tables.
```

Renumber any instructions after this one if the list numbering is sequential (check the full list with `grep -n "^[0-9]*\." fill_narratives.py` first).

- [ ] **Step 2: Commit**

```bash
git add fill_narratives.py
git commit -m "Extend anti-fabrication rules to Market Breadth and weekly movers tables"
```

---

### Task 7: Full pipeline dry-run (generate + fill, no push, no Discord)

**Files:** none (verification only)

- [ ] **Step 1: Run generate + fill against the same 2020-01-02 scratch date, skip everything after**

```bash
cd /Users/TGore/Lucren/GlobalMarkets-Investor
/usr/local/bin/python3 generate_report.py --type open --date 2020-01-02
/usr/local/bin/python3 fill_narratives.py Open/Open_01-02-20.md --date 2020-01-02
```

- [ ] **Step 2: Inspect the result**

Run: `grep -A6 "## Market Breadth" Open/Open_01-02-20.md`

Expected: real numbers in every row, "S&P 500" labels (never "NYSE"/"Nasdaq"), and — critically — the numbers must be **unchanged** from what `generate_report.py` wrote (confirms `fill_narratives.py`'s Task 6 rule held and Claude didn't rewrite them). Compare against the printed breadth stats from generate_report.py's own console output in Step 1.

- [ ] **Step 3: Clean up the scratch file — this was never a real report**

```bash
rm -f Open/Open_01-02-20.md
```

- [ ] **Step 4: Confirm no real report files were touched**

```bash
git status --short Open/ Close/ Weekly/
```

Expected: no output (or only the pre-existing dirty-by-design private-content-ideas diffs that predate this session — compare against `git status` output from before Task 1 if unsure).
