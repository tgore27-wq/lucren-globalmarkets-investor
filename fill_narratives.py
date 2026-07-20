#!/usr/bin/env python3
"""
fill_narratives.py
Reads a generated investor report (price tables already populated),
fetches today's top market news via Alpha Vantage, then calls the
Claude API to fill every blank narrative section.

Usage:
  python fill_narratives.py --today          # open + close for today
  python fill_narratives.py --weekly         # weekly for current week
  python fill_narratives.py --all            # open + close + weekly
  python fill_narratives.py Open/Open_06-30-26.md
  python fill_narratives.py Close/Close_06-30-26.md Weekly/Weekly_06-29-26.md
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

try:
    import anthropic
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic", "-q"])
    import anthropic

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE = Path(__file__).parent

def load_env():
    cfg = {}
    for f in [BASE / ".env", Path.home() / ".env"]:
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    # Allow env vars to override .env
    for key in ("ANTHROPIC_API_KEY", "ALPHA_VANTAGE_API_KEY"):
        if key in os.environ:
            cfg[key] = os.environ[key]
    return cfg

ENV = load_env()
ANTHROPIC_KEY = ENV.get("ANTHROPIC_API_KEY", "")
AV_KEY = ENV.get("ALPHA_VANTAGE_API_KEY", "")

# ---------------------------------------------------------------------------
# News fetching (Alpha Vantage — free tier, 25 calls/day)
# ---------------------------------------------------------------------------

AV_NEWS_TICKERS = "SPY,QQQ,NVDA,AAPL,MSFT,TSLA,AMD,JPM,XOM"

def fetch_news(limit: int = 20) -> str:
    """Return a text block of today's top market headlines."""
    if not AV_KEY:
        return "(No Alpha Vantage key — news unavailable.)"
    try:
        url = (
            "https://www.alphavantage.co/query"
            f"?function=NEWS_SENTIMENT"
            f"&tickers={AV_NEWS_TICKERS}"
            f"&sort=LATEST"
            f"&limit={limit}"
            f"&apikey={AV_KEY}"
        )
        r = requests.get(url, timeout=15)
        data = r.json()
        items = data.get("feed", [])
        if not items:
            return "(No news returned by Alpha Vantage.)"
        lines = []
        for item in items[:limit]:
            title = item.get("title", "")
            source = item.get("source", "")
            summary = item.get("summary", "")[:200]
            tickers = ", ".join(
                t["ticker"] for t in item.get("ticker_sentiment", [])[:4]
            )
            lines.append(f"• [{source}] {title}")
            if summary:
                lines.append(f"  {summary}")
            if tickers:
                lines.append(f"  Related: {tickers}")
        return "\n".join(lines)
    except Exception as e:
        return f"(News fetch error: {e})"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a senior market analyst and financial writer at an institutional
investment firm. Your job is to complete investor-grade daily and weekly
market reports by filling in every blank or placeholder section.

RULES:
1. Do NOT change any existing data — prices, percentages, table values,
   dates, or headers. Preserve them exactly as written.
2. Fill ONLY sections that contain placeholders: "[Fill in]", empty "- ",
   blank table cells (| |), or text like "Bullish / Cautiously Bullish /
   Neutral / Cautious / Bearish".
3. Base all analysis on the price data already in the report plus the
   market news context provided. Do not invent numbers.
CRITICAL — NEVER FABRICATE THESE:
A. Analyst Actions: NEVER invent analyst upgrades, downgrades, initiations,
   or price targets. If the Analyst Actions table contains "No actions
   reported today" or "—", leave it exactly as-is. Do not add rows,
   tickers, firms, grades, or price targets that are not already in the
   data. A fabricated price target published to investors is misinformation.
B. Specific company events: Do not invent earnings results, guidance
   changes, M&A activity, or regulatory actions for named companies.
C. Economic data: Do not fabricate specific economic release numbers
   (CPI prints, payroll counts, PMI readings, etc.) unless they are
   already present in the report.
4. Market Tone choices (pick one): Bullish | Cautiously Bullish | Neutral |
   Cautious | Bearish
5. TL;DR: 4 concise bullets summarising the session's most important events.
6. Market Summary: 2-4 sentences of professional narrative prose.
7. Opportunities and Risks: 3 specific, actionable bullets each.
8. Geopolitical & Macro: short phrases, not long paragraphs.
9. Key Levels: fill Support, Resistance, Key Level, Notes for each row.
10. Sentiment Gauges: use CNN Fear & Greed value if present; estimate
    "Greed/Fear/Extreme Fear/Extreme Greed" from VIX and price action if not.
11. Earnings Calendar: fill in the most relevant earnings for this week
    based on context; use "—" if unknown.
12. Fed Watch: derive from current rate (shown in report) and recent
    yield-curve data.
13. After-Hours / Pre-Market Movers: if Catalyst column is blank, infer
    from the biggest daily movers in the sector ETF table.
14. Weekly sector rotation narrative: explain which sectors led/lagged
    and why, based on weekly % columns.
15. Return the COMPLETE report with every section filled. Output ONLY
    the report markdown — no commentary before or after.
"""

# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

def fill_with_claude(report_path: Path, news_text: str, report_date: str) -> str:
    """Call Claude API and return fully filled report markdown."""
    if not ANTHROPIC_KEY:
        print(f"  [ERROR] ANTHROPIC_API_KEY not set — cannot fill narratives.")
        return report_path.read_text()

    content = report_path.read_text()
    fname = report_path.name

    try:
        from generate_report import market_holiday
        holiday = market_holiday(report_date)
    except Exception:
        holiday = None

    holiday_block = ""
    if holiday:
        from datetime import datetime as _dt, timedelta as _td
        from generate_report import market_holiday as _mh
        _d = _dt.strptime(report_date, "%Y-%m-%d").date()
        _prev = _d - _td(days=1)
        while _prev.weekday() >= 5 or _mh(_prev.strftime("%Y-%m-%d")):
            _prev -= _td(days=1)
        _next = _d + _td(days=1)
        while _next.weekday() >= 5 or _mh(_next.strftime("%Y-%m-%d")):
            _next += _td(days=1)
        prev_str = _prev.strftime("%A, %B %-d, %Y")
        next_str = _next.strftime("%A, %B %-d, %Y")
        holiday_block = f"""
=== CRITICAL: US MARKET HOLIDAY ===
US equity markets (NYSE/Nasdaq) are CLOSED today for {holiday}. There is NO
US trading session today.
EXACT DATES — use these verbatim, do NOT compute dates yourself:
- Last completed US trading session: {prev_str}
- Next US trading session: {next_str} The US index, sector ETF, volatility, and yield
data in this report are carried over from the LAST COMPLETED trading session.
You MUST write every narrative section accordingly:
- State clearly and early that US markets are closed today for {holiday}
  and name the next trading day.
- Describe all US equity/sector/VIX figures as "as of the last session's
  close" — NEVER as intraday action happening today.
- International markets, crypto, and some commodity/futures data may reflect
  genuine trading today and can be described as today's moves.
- No US economic data is released today (federal holiday). Do not list any
  US releases in today's economic calendar; mark it closed/none.
- Do not describe volume, liquidity, breadth, or a "session" for US equities
  today — there is none.
"""

    user_message = f"""\
Report date: {report_date}
File: {fname}
{holiday_block}
=== MARKET NEWS CONTEXT ===
{news_text}

=== REPORT TO COMPLETE ===
{content}
"""

    # Explicit timeout + bounded retries as a backstop (see below for the
    # actual fix — this just keeps any residual stall bounded rather than
    # hanging indefinitely).
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY, timeout=90.0, max_retries=1)
    print(f"  Calling Claude API for {fname}...")

    try:
        # Root cause of the repeated "Request timed out or interrupted"
        # failures (2026-07-15, -16 x4, -17, -20): this is a non-streaming
        # call with max_tokens=8192, which per Anthropic's own docs
        # (platform.claude.com/docs/en/api/errors#long-requests) sits on an
        # idle connection while the full response generates — exactly the
        # condition their docs warn "some networks may drop... after a
        # variable period of time." Streaming keeps data flowing throughout
        # generation instead of idling, which is their documented fix, and
        # get_final_message() still returns the identical assembled Message.
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            message = stream.get_final_message()
        return message.content[0].text
    except Exception as e:
        print(f"  [ERROR] Claude API call failed: {e}")
        return content   # return original if API fails

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_trading_day(date: datetime) -> bool:
    if date.weekday() >= 5:  # Sat=5, Sun=6
        return False
    # Juneteenth 2026
    if (date.year == 2026 and date.month == 6 and date.day == 19):
        return False
    # Independence Day observed (Jul 3 when Jul 4 is Sat)
    if (date.year == 2026 and date.month == 7 and date.day == 3):
        return False
    return True

def week_monday(d: datetime) -> datetime:
    return d - timedelta(days=d.weekday())

def report_date_from_path(path: Path) -> str:
    """Extract YYYY-MM-DD from filename like Open_06-30-26.md"""
    stem = path.stem  # e.g. "Open_06-30-26"
    parts = stem.split("_", 1)
    if len(parts) < 2:
        return datetime.now().strftime("%Y-%m-%d")
    date_part = parts[1]  # "06-30-26"
    p = date_part.split("-")
    if len(p) == 3:
        return f"20{p[2]}-{p[0]}-{p[1]}"
    return datetime.now().strftime("%Y-%m-%d")

def _split_preamble_and_sections(text):
    """Split a report into (preamble_before_first_H2, [(h2_title, full_section_text)])."""
    lines = text.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip().startswith("## "):
        i += 1
    preamble = "\n".join(lines[:i])
    sections = []
    cur_title, cur_lines = None, []
    for line in lines[i:]:
        if line.strip().startswith("## "):
            if cur_title is not None:
                sections.append((cur_title, "\n".join(cur_lines)))
            cur_title = line.strip()[3:].strip()
            cur_lines = [line]
        else:
            cur_lines.append(line)
    if cur_title is not None:
        sections.append((cur_title, "\n".join(cur_lines)))
    return preamble, sections


_BLANK_CELL_RE = re.compile(r'\|\s*\|')
_PLACEHOLDER_RE = re.compile(r'\[Fill in\]|Bullish / Cautiously Bullish', re.IGNORECASE)
_BLANK_BOLD_LABEL_RE = re.compile(r'^\*\*.+?:\*\*\s*$')


def _section_is_fully_populated(section_text: str) -> bool:
    """True if a section's table(s) already had every cell filled in — i.e. it
    was real data written by generate_report.py, not a placeholder for Claude
    to complete. Sections with no table at all (Market Tone, Fed Watch,
    Opportunities, ...) are narrative-only and are never considered locked.

    Also checks for blank bold-label lines like "**Sector rotation
    narrative:**" with nothing after the colon — several report sections
    (e.g. Weekly's "Sector Performance") pair a fully-numeric table with one
    of these narrative labels for Claude to complete. Missing this let the
    guard incorrectly treat the whole section as locked and discard Claude's
    legitimate narrative fill along with it (caught 2026-07-20, Weekly
    "Sector Performance — Week": the guard fired and reverted a real,
    non-corrupted sector-rotation writeup back to blank)."""
    if _PLACEHOLDER_RE.search(section_text):
        return False
    has_table = False
    for line in section_text.split("\n"):
        s = line.strip()
        if s.startswith("|"):
            has_table = True
            if _BLANK_CELL_RE.search(s):
                return False
        elif _BLANK_BOLD_LABEL_RE.match(s):
            return False
    return has_table


def guard_against_corruption(original: str, filled: str) -> str:
    """Defense against LLM transcription drift.

    fill_with_claude() asks Claude to transcribe the ENTIRE report back,
    including data tables that were already 100% populated before the call —
    it only needs to *add* text to blank/placeholder sections. Asking a model
    to reproduce large verbatim tables alongside genuinely-generated content
    is a known way to get a duplicated or dropped row (this is exactly what
    happened to the Sector ETFs table in the 2026-07-09 close report — an
    extra Consumer Discretionary row appeared with no code path that could
    have produced it).

    Any section that was already fully populated (no blank cells, no
    placeholders) in the original is restored verbatim here, regardless of
    what Claude returned for it — only genuinely-blank sections are Claude's
    to fill.
    """
    _, orig_sections = _split_preamble_and_sections(original)
    orig_map = dict(orig_sections)
    filled_preamble, filled_sections = _split_preamble_and_sections(filled)

    repaired = [filled_preamble]
    seen_titles = set()
    for title, text in filled_sections:
        seen_titles.add(title)
        orig_text = orig_map.get(title)
        if orig_text is not None and _section_is_fully_populated(orig_text) and text.rstrip() != orig_text.rstrip():
            print(f"  [GUARD] '{title}' was altered by Claude despite being fully "
                  f"populated before the API call — restoring original verbatim.")
            repaired.append(orig_text)
        else:
            repaired.append(text)

    for title, orig_text in orig_sections:
        if title not in seen_titles and _section_is_fully_populated(orig_text):
            print(f"  [GUARD] '{title}' was dropped by Claude — re-inserting original verbatim.")
            repaired.append(orig_text)

    return "\n".join(repaired)


def fill_file(path: Path, news_text: str):
    """Fill narratives for a single report file."""
    if not path.exists():
        print(f"  [SKIP] {path} not found.")
        return
    report_date = report_date_from_path(path)
    print(f"  Filling {path.name} (date: {report_date})")
    original = path.read_text()
    filled = fill_with_claude(path, news_text, report_date)
    filled = guard_against_corruption(original, filled)
    path.write_text(filled)
    print(f"  ✓ {path.name} saved.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fill narrative sections via Claude API")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--today",   action="store_true", help="Open + Close for today")
    group.add_argument("--weekly",  action="store_true", help="Weekly for current week")
    group.add_argument("--monthly", action="store_true", help="Monthly report (defaults to previous month)")
    group.add_argument("--all",     action="store_true", help="Open + Close + Weekly")
    parser.add_argument("files",    nargs="*",           help="Specific .md files to fill")
    parser.add_argument("--date",   default=None,        help="Override date YYYY-MM-DD")
    parser.add_argument("--month",  default=None,        help="Override month YYYY-MM (for --monthly)")
    args = parser.parse_args()

    today = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()
    date_str = today.strftime("%m-%d-%y")   # 06-30-26
    mon = week_monday(today)
    mon_str = mon.strftime("%m-%d-%y")

    print(f"\n=== fill_narratives.py | {today.strftime('%Y-%m-%d')} ===\n")
    print("Fetching market news...")
    news_text = fetch_news(limit=25)
    print(f"  Got {news_text.count(chr(10))} lines of news context.\n")

    targets: list[Path] = []

    if args.files:
        targets = [BASE / f for f in args.files]
    elif args.today:
        targets = [
            BASE / "Open"  / f"Open_{date_str}.md",
            BASE / "Close" / f"Close_{date_str}.md",
        ]
    elif args.weekly:
        targets = [BASE / "Weekly" / f"Weekly_{mon_str}.md"]
    elif args.monthly:
        if args.month:
            yr, mo = int(args.month[:4]), int(args.month[5:7])
        else:
            first = today.replace(day=1)
            prev  = first - timedelta(days=1)
            yr, mo = prev.year, prev.month
        from datetime import datetime as _dt
        month_slug = _dt(yr, mo, 1).strftime("%m-%Y")
        targets = [BASE / "Monthly" / f"Monthly_{month_slug}.md"]
    elif args.all:
        targets = [
            BASE / "Open"   / f"Open_{date_str}.md",
            BASE / "Close"  / f"Close_{date_str}.md",
            BASE / "Weekly" / f"Weekly_{mon_str}.md",
        ]
    else:
        # Default: fill all files that have placeholder text
        for folder in ("Open", "Close", "Weekly", "Monthly"):
            for f in sorted((BASE / folder).glob("*.md")):
                if "Template" in f.name:
                    continue
                content = f.read_text()
                if "[Fill in]" in content or "- \n- \n- " in content:
                    targets.append(f)
        if not targets:
            print("No unfilled reports found. Pass --today, --weekly, --monthly, or file paths.")
            return

    for path in targets:
        fill_file(path, news_text)
        time.sleep(2)   # brief pause between API calls

    print("\n✓ All done.")

if __name__ == "__main__":
    main()
