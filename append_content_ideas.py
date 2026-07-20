#!/usr/bin/env python3
"""
append_content_ideas.py  —  PRIVATE, LOCAL USE ONLY
Generates 10 Lucren content ideas from the day's market report using Claude
and appends them to the local copy. This file is never committed to GitHub
and the content ideas section never appears in public reports or Discord.

Usage:
  python append_content_ideas.py --open               # today's open report
  python append_content_ideas.py --close              # today's close report
  python append_content_ideas.py --weekly             # this week's weekly report
  python append_content_ideas.py --monthly            # previous month's report
  python append_content_ideas.py Open/Open_06-29-26.md   # explicit file
  python append_content_ideas.py --date 2026-06-29 --open
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

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
MARKER = "## Lucren Content Ideas"


def load_env():
    cfg = {}
    for f in [BASE / ".env", Path.home() / ".env"]:
        if f.exists():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    if "ANTHROPIC_API_KEY" in os.environ:
        cfg["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
    return cfg


ENV = load_env()
ANTHROPIC_KEY = ENV.get("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a creative content strategist for Lucren, a retail investor community
and financial platform. Your job is to generate high-quality, platform-specific
content ideas based on today's real market data.

Lucren's audience: retail investors ranging from beginners to intermediate.
The community receives daily market updates and trade ideas from the founder.
Lucren's tone: clear, confident, educational, and actionable — not hype.

Generate exactly 10 content ideas inspired by today's specific market events,
price moves, and themes from the report provided. Each idea must be:
- Tied directly to something that actually happened in today's market
- Ready to execute (specific enough to act on immediately)
- Labeled with the content type and platform

Content types to draw from (use a mix, don't repeat the same type more than twice):
  • Twitter/X Thread — numbered multi-tweet breakdown of a market concept or move
  • Instagram Carousel — slide-by-slide visual education post (specify slide titles)
  • Community Post — discussion prompt or update for the Lucren Discord
  • Newsletter Section — a section topic for Lucren's weekly investor newsletter
  • Short-Form Video — 30-60 second TikTok/Reel concept with hook and key point
  • YouTube Topic — longer-form explainer or market recap concept (5-15 min)
  • Podcast Talking Point — a specific segment topic for a markets podcast episode
  • Infographic Idea — visual data story concept (specify what data to visualize)
  • Poll / Engagement — a community poll question with 3-4 answer options
  • Trade Education — a lesson framed around a real move that happened today

FORMAT — return exactly this structure, nothing else:

## Lucren Content Ideas — {date}

> *Private — Lucren internal use only. Do not share or publish this section.*

1. **[Content Type | Platform]** — [Specific idea tied to today's market]
   *Hook/Angle:* [One sentence on the hook or opening line]

2. **[Content Type | Platform]** — [Specific idea tied to today's market]
   *Hook/Angle:* [One sentence on the hook or opening line]

[...continue through 10...]

---
"""

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def already_has_ideas(content: str) -> bool:
    return MARKER in content


def generate_ideas(report_content: str, report_date: str) -> str:
    if not ANTHROPIC_KEY:
        return (
            f"\n\n## Lucren Content Ideas — {report_date}\n\n"
            "> *Private — Lucren internal use only.*\n\n"
            "_Content ideas unavailable: ANTHROPIC_API_KEY not set in .env_\n\n---\n"
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY, timeout=90.0, max_retries=1)

    user_message = (
        f"Report date: {report_date}\n\n"
        f"=== MARKET REPORT ===\n{report_content}\n"
    )

    print(f"  Calling Claude API for content ideas ({report_date})...")
    try:
        # Streaming instead of a blocking create() call — see fill_narratives.py's
        # fill_with_claude() for why (idle-connection drops on non-streaming
        # requests; Anthropic's documented fix for exactly this failure mode).
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=SYSTEM_PROMPT.format(date=report_date),
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            message = stream.get_final_message()
        return "\n\n" + message.content[0].text.strip() + "\n"
    except Exception as e:
        print(f"  [ERROR] Claude API failed: {e}")
        return (
            f"\n\n## Lucren Content Ideas — {report_date}\n\n"
            f"> *Private — Lucren internal use only.*\n\n"
            f"_Content ideas generation failed: {e}_\n\n---\n"
        )


def append_to_report(path: Path, report_date: str) -> bool:
    if not path.exists():
        print(f"  [SKIP] {path.name} not found.")
        return False

    content = path.read_text(encoding="utf-8")

    if already_has_ideas(content):
        print(f"  [SKIP] {path.name} already has content ideas.")
        return True

    print(f"  Generating ideas for {path.name}...")
    ideas_block = generate_ideas(content, report_date)

    # Strip trailing whitespace/newlines from report, then append
    updated = content.rstrip() + "\n" + ideas_block
    path.write_text(updated, encoding="utf-8")
    print(f"  ✓ Content ideas appended to {path.name}")
    return True


def date_from_path(path: Path) -> str:
    """Extract YYYY-MM-DD from filename like Open_06-29-26.md"""
    stem = path.stem
    parts = stem.split("_", 1)
    if len(parts) < 2:
        return datetime.now().strftime("%Y-%m-%d")
    dp = parts[1].split("-")
    if len(dp) == 3:
        try:
            return f"20{dp[2]}-{dp[0]}-{dp[1]}"
        except Exception:
            pass
    if len(dp) == 2:
        # Monthly slug: 06-2026
        try:
            return f"{dp[1]}-{dp[0]}-01"
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m-%d")


def week_monday(d: datetime) -> datetime:
    return d - timedelta(days=d.weekday())

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Append Lucren content ideas to local market reports (private only)"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--open",    action="store_true", help="Today's open report")
    group.add_argument("--close",   action="store_true", help="Today's close report")
    group.add_argument("--weekly",  action="store_true", help="This week's weekly report")
    group.add_argument("--monthly", action="store_true", help="Previous month's monthly report")
    parser.add_argument("files",    nargs="*",           help="Explicit .md file path(s)")
    parser.add_argument("--date",   default=None,        help="Override date YYYY-MM-DD")
    parser.add_argument("--month",  default=None,        help="Override month YYYY-MM (for --monthly)")
    args = parser.parse_args()

    today = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()
    date_str = today.strftime("%m-%d-%y")
    mon_str  = week_monday(today).strftime("%m-%d-%y")

    print(f"\n=== append_content_ideas.py | {today.strftime('%Y-%m-%d')} ===\n")

    targets: list[tuple[Path, str]] = []

    if args.files:
        for f in args.files:
            p = Path(f) if Path(f).is_absolute() else BASE / f
            targets.append((p, date_from_path(p)))

    elif args.open:
        p = BASE / "Open" / f"Open_{date_str}.md"
        targets.append((p, today.strftime("%Y-%m-%d")))

    elif args.close:
        p = BASE / "Close" / f"Close_{date_str}.md"
        targets.append((p, today.strftime("%Y-%m-%d")))

    elif args.weekly:
        p = BASE / "Weekly" / f"Weekly_{mon_str}.md"
        targets.append((p, week_monday(today).strftime("%Y-%m-%d")))

    elif args.monthly:
        if args.month:
            yr, mo = int(args.month[:4]), int(args.month[5:7])
        else:
            first = today.replace(day=1)
            prev  = first - timedelta(days=1)
            yr, mo = prev.year, prev.month
        month_slug = datetime(yr, mo, 1).strftime("%m-%Y")
        p = BASE / "Monthly" / f"Monthly_{month_slug}.md"
        targets.append((p, datetime(yr, mo, 1).strftime("%Y-%m-%d")))

    else:
        parser.print_help()
        return

    for path, report_date in targets:
        append_to_report(path, report_date)

    print("\n✓ Done.")


if __name__ == "__main__":
    main()
