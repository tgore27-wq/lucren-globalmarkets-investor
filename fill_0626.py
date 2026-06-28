#!/usr/bin/env python3
"""
Fills qualitative sections for June 26 Open, Close, and Weekly_06-22-26 reports.
"""
import re
from pathlib import Path

BASE = Path(__file__).parent

# ---------------------------------------------------------------------------
# Shared helpers (same as fill_qualitative.py)
# ---------------------------------------------------------------------------

def load(p): return p.read_text()
def save(p, c): p.write_text(c)

def replace_section(content, marker, new_content):
    idx = content.find(marker)
    if idx == -1:
        return content
    end_idx = content.find("\n---", idx)
    if end_idx == -1:
        end_idx = len(content)
    return content[:idx] + new_content + content[end_idx:]

def build_tone(tone, tldr):
    lines = [f"## Market Tone\n**Overall:** {tone}\n\n**TL;DR:**"]
    for b in tldr:
        lines.append(f"- {b}")
    lines.append("")
    return "\n".join(lines) + "\n"

def build_sentiment(fg_score, fg_label, bulls, bears, neutral, reading=""):
    return (
        f"## Sentiment Gauges\n\n"
        f"- **CNN Fear & Greed Index:** {fg_score} — {fg_label}\n"
        f"- **AAII Sentiment (latest weekly):** Bulls {bulls}% | Bears {bears}% | Neutral {neutral}%\n"
        f"- **Reading:** {reading}\n"
    )

def build_geopolitical(global_, us, energy, dxy, yield10):
    return (
        f"## Geopolitical & Macro Developments\n\n"
        f"- **Global:** {global_}\n"
        f"- **US:** {us}\n"
        f"- **Energy Markets:** {energy}\n"
        f"- **Currency (DXY):** {dxy}\n"
        f"- **Bond Market (10Y Yield):** {yield10}\n"
    )

def build_key_levels(levels):
    rows = "\n".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |" for r in levels)
    return (
        f"## Morning Setup — Key Levels to Watch\n\n"
        f"| Index / Asset | Support | Resistance | Key Level | Notes |\n"
        f"|---------------|---------|------------|-----------|-------|\n"
        f"{rows}\n"
    )

def build_earnings_calendar(earnings):
    rows = "\n".join(
        f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} |"
        for r in earnings
    )
    return (
        f"## Earnings Calendar — This Week\n\n"
        f"| Day | Ticker | Company | Time | EPS Est | Rev Est | Implied Move |\n"
        f"|-----|--------|---------|------|---------|---------|---------------|\n"
        f"{rows}\n"
    )

def build_fed_watch_open(fomc, fed_rate, commentary, prob):
    return (
        f"## Fed Watch\n\n"
        f"- **Next FOMC Meeting:** {fomc}\n"
        f"- **Current Fed Funds Rate:** {fed_rate}\n"
        f"- **Overnight Fed Commentary:** {commentary}\n"
        f"- **Rate Change Probability (CME FedWatch):** {prob}\n"
    )

def build_fed_watch_close(fomc, fed_rate, prob, activity, speaker, quote):
    return (
        f"## Fed Watch\n\n"
        f"- **Today's Fed Activity:** {activity}\n"
        f"- **Current Fed Funds Rate:** {fed_rate}\n"
        f"- **Rate Change Probability (CME FedWatch):** {prob}\n"
        f"- **Next FOMC Meeting:** {fomc}\n"
        f"- **Notable Fed Speaker(s) Today:** {speaker}\n"
        f"- **Key Quote:** {quote}\n"
    )

def build_ms(summary): return f"## 1. Market Summary\n\n{summary}\n"
def build_opps(opps):
    return "## 2. Opportunities\n\n" + "\n".join(f"- {o}" for o in opps) + "\n"
def build_risks(risks):
    return "## 3. Risks\n\n" + "\n".join(f"- {r}" for r in risks) + "\n"

def build_premarket(gainers, losers):
    def rows(items):
        return "\n".join(f"| {t} | {c} | {p} | {cat} |" for t, c, p, cat in items)
    return (
        f"## Pre-Market Movers\n\n"
        f"### Pre-Market Gainers\n"
        f"| Ticker | Company | % Change | Catalyst |\n"
        f"|--------|---------|----------|----------|\n"
        f"{rows(gainers)}\n\n"
        f"### Pre-Market Losers\n"
        f"| Ticker | Company | % Change | Catalyst |\n"
        f"|--------|---------|----------|----------|\n"
        f"{rows(losers)}\n"
    )

def build_afterhours(gainers, losers):
    def rows(items):
        return "\n".join(f"| {t} | {c} | {p} | {cat} |" for t, c, p, cat in items)
    return (
        f"## After-Hours Movers\n\n"
        f"### After-Hours Gainers\n"
        f"| Ticker | Company | % Change | Catalyst |\n"
        f"|--------|---------|----------|----------|\n"
        f"{rows(gainers)}\n\n"
        f"### After-Hours Losers\n"
        f"| Ticker | Company | % Change | Catalyst |\n"
        f"|--------|---------|----------|----------|\n"
        f"{rows(losers)}\n"
    )

# ---------------------------------------------------------------------------
# June 26 data
# ---------------------------------------------------------------------------

DATE = "2026-06-26"

TONE = "Bearish"
TLDR = [
    "Nasdaq posts its 5th consecutive losing session (−0.24% to 25,298) — longest skid since February 2026",
    "OpenAI reportedly delays IPO to 2027 after SpaceX's post-debut decline; Intel −3%, Arm −4%, Marvell −3.7%",
    "Dow +0.14% and Russell 2000 +0.07% outperform as investors rotate into defensives to close H1 2026",
    "S&P 500 finishes H1 at 7,354 (+7.43% YTD); Nasdaq +8.84% YTD despite June's 4.5% weekly drop",
]

FG = ("25", "Fear")
AAII = ("34", "37", "29")
AAII_READING = "Consecutive bearish readings mark the most pessimistic stretch since March 2026; typical contrarian signal"

GEO = {
    "global": "Asian markets fell sharply overnight: Japan Nikkei −4.15%, Korea KOSPI −5.81% on semiconductor contagion from US AI selloff and OpenAI IPO delay news. European indices also lower.",
    "us": "OpenAI reportedly considering pushing IPO to 2027 (NY Times, June 25) — citing SpaceX's post-debut decline from $225 ATH to ~$153 as caution signal. End-of-quarter H1 portfolio rebalancing adds selling pressure in tech.",
    "energy": "WTI Crude Oil −3.74% to $69.23 as Strait of Hormuz mine-clearing progresses — most significant single-day oil drop since Iran MOU. Iran deal implementation on track.",
}
DXY = "120.40"
YIELD = "4.40%"

KEY_LEVELS = [
    ("S&P 500",  "7,280", "7,420", "7,354 close", "H1 closes at 7,354 — watch 7,280 for capitulation signal or bounce"),
    ("Nasdaq",   "25,000", "25,800", "25,298 close", "5th down day; 25,000 is critical floor — break opens path to 24,500"),
    ("BTC",      "57,000", "63,000", "60,026 close", "Crypto holding 60K despite equity weakness"),
    ("Gold",     "3,980", "4,150", "4,072 close", "Gold +1.44% as safe haven demand rises; H2 2026 positioning"),
]

EARNINGS_WEEK = [
    ("Tue", "FDX", "FedEx Q4 FY26", "After", "Beat $6.41 EPS", "$25.0B rev", "Strong +4%"),
    ("Wed AH", "MU", "Micron Q3 FY26", "After", "$25.11 EPS", "$41.5B rev", "Blowout +17%"),
    ("Next Tue", "NKE", "Nike Q4 FY26", "Jun 30 After", "$0.12 EPS est", "$10.85B est", "H2 pivotal"),
]

FED_FOMC = "Late July 2026"
FED_RATE = "3.63% (range 3.50–3.75%)"
FED_COMMENTARY = "Post-FOMC: Fed officials maintaining hawkish tone. 10-Year yield falling to 4.40% from 4.51% Monday — market repricing as oil drops and inflation pressure eases."
FED_PROB = "~60% year-end hike; July hold near-certain (~92%); yields declining as oil-driven inflation expectations ease"
FED_ACTIVITY_CLOSE = "No FOMC activity. Several Fed speakers maintained 'data dependent' stance through the week."
FED_SPEAKER = "None scheduled"
FED_QUOTE = "'More progress is needed before adjusting policy.' — Fed official consensus language"

PM_GAINERS = [
    ("XLV", "Healthcare Select SPDR", "+1.2%", "Defensive rotation as OpenAI/tech news hits growth"),
    ("GLD", "SPDR Gold Trust", "+1.3%", "Safe-haven demand; Asian markets down sharply overnight"),
    ("UNH", "UnitedHealth Group", "+0.8%", "Healthcare sector leadership in risk-off environment"),
]
PM_LOSERS = [
    ("INTC", "Intel", "-3.0%", "OpenAI IPO delay signals AI demand uncertainty"),
    ("MRVL", "Marvell Technology", "-3.7%", "AI chip demand concerns reignite"),
    ("SPCX", "SpaceX", "-2.0%", "Near listing price $152; OpenAI delay sees SPCX cited as cautionary tale"),
    ("ARM",  "Arm Holdings", "-4.0%", "AI semiconductor complex hit by OpenAI delay news"),
]

AH_GAINERS = [
    ("—", "Quiet end-of-quarter", "—", "H1 rebalancing complete; no major earnings tonight"),
]
AH_LOSERS = [
    ("—", "Quiet end-of-quarter", "—", "AI sector weakness sustained but no major new catalysts"),
]

MARKET_SUMMARY_OPEN = (
    "Markets head into Friday's final H1 session facing compounding headwinds. Asian bourses suffered sharp overnight losses — Japan's Nikkei fell 4.15% and Korea's KOSPI plunged 5.81%, the worst drop since April — as the NY Times report that OpenAI is considering delaying its 2026 IPO to 2027 spread through global semiconductor ecosystems. OpenAI cited SpaceX's rapid decline from its ATH of $225.64 to ~$153 as evidence that the IPO window for AI-adjacent names has narrowed. The report sent Intel, Marvell, Arm, and Sandisk sharply lower in pre-market trading. Today is also the final day of Q2 and H1 2026, meaning institutional rebalancing and window dressing are complete — leaving pure price discovery for Friday's session. Oil continues to fall sharply on Hormuz reopening momentum, which may ultimately moderate Fed hawkishness but won't be reflected in the FOMC's data for several weeks."
)
OPPS_OPEN = [
    "Gold and defensive healthcare as H2 2026 positioning vehicles — both outperforming as rate/growth expectations reset",
    "End-of-H1 rebalancing overhang clears after today — Q3 typically has lighter institutional selling pressure",
    "Oil normalization timeline accelerating: WTI at $69 means CPI could fall significantly by September print",
]
RISKS_OPEN = [
    "OpenAI IPO delay signals the AI IPO window has closed for 2026 — private-market AI valuations may need to reprice",
    "Asian semiconductor contagion: Korea KOSPI −5.81% suggests Samsung/SK Hynix facing same demand questions as US chip stocks",
    "Nasdaq 5-day losing streak technically bearish; if 25,000 fails, June lows are 5%+ lower from current levels",
]

MARKET_SUMMARY_CLOSE = (
    "The first half of 2026 ended as it had frequently traded: with technology dragging the Nasdaq lower while the broader market held in. The S&P 500 barely moved (−0.05%) and the Dow Jones closed slightly down (−0.09%), but the Nasdaq logged its fifth consecutive losing session (−0.24%), the longest such stretch since February 2026. The session's defining story was OpenAI's reported IPO delay to 2027 — a reversal that hit Intel, Arm, Marvell, and other AI infrastructure names hard. SpaceX closed around $152, barely above its $135 IPO price and well off its June 17 all-time high of $225.64, serving as the cautionary tale OpenAI cited for its delay. On a positive note, oil's 3.74% decline on Strait of Hormuz reopening progress provided a meaningful signal that the energy-driven inflation shock is easing. H1 2026 final scorecard: S&P 500 +7.43% YTD, Nasdaq +8.84% YTD, Dow +7.93% YTD — solid gains despite a turbulent second half of June."
)
OPPS_CLOSE = [
    "H2 2026 setup: oil normalization reduces CPI, which may allow Fed to hold through Q3 — a bullish scenario for rate-sensitive sectors",
    "Semiconductor names at multi-week lows with fundamentals intact (Micron just proved record demand) — patient entry attractive",
    "Nike Q4 FY2026 reports June 30 — low expectations ($0.12 EPS estimate, 45% revision lower) set up for a potential beat catalyst",
]
RISKS_CLOSE = [
    "OpenAI delay may be the start of a broader AI IPO withdrawal — private valuations and public AI sentiment could decouple further",
    "Asian semiconductor collapse (Korea KOSPI −5.81%) signals global demand concerns are spreading beyond US equities",
    "Nasdaq broke 5 support levels in 5 sessions — technical momentum firmly bearish heading into H2 2026; July FOMC risk remains",
]

# ---------------------------------------------------------------------------
# Fill June 26 Open
# ---------------------------------------------------------------------------

def fill_open():
    path = BASE / "Open" / "Open_06-26-26.md"
    c = load(path)

    c = replace_section(c, "## Market Tone", build_tone(TONE, TLDR))
    c = replace_section(c, "## Earnings Calendar — This Week", build_earnings_calendar(EARNINGS_WEEK))
    c = replace_section(c, "## Fed Watch", build_fed_watch_open(FED_FOMC, FED_RATE, FED_COMMENTARY, FED_PROB))
    c = replace_section(c, "## Geopolitical & Macro Developments",
                        build_geopolitical(GEO["global"], GEO["us"], GEO["energy"], DXY, YIELD))
    c = replace_section(c, "## Morning Setup — Key Levels to Watch", build_key_levels(KEY_LEVELS))
    c = replace_section(c, "## Sentiment Gauges", build_sentiment(*FG, *AAII, AAII_READING))
    c = replace_section(c, "## Pre-Market Movers", build_premarket(PM_GAINERS, PM_LOSERS))
    c = replace_section(c, "## 1. Market Summary", build_ms(MARKET_SUMMARY_OPEN))
    c = replace_section(c, "## 2. Opportunities", build_opps(OPPS_OPEN))
    c = replace_section(c, "## 3. Risks", build_risks(RISKS_OPEN))

    # Add overnight note to international markets table
    intl_notes = {
        "Japan":       "Sharp AI/tech contagion; semiconductor sector hit hard",
        "South Korea": "KOSPI worst day since April; Samsung/SK Hynix drag on chip fears",
        "Germany":     "European tech/industrials weaker; DXY pressure",
        "UK":          "Defensive; FTSE outperforms as energy & financials hold",
        "Hong Kong":   "Tech selloff extends to HK; Hang Seng risk-off",
        "China":       "Tech sector weakness; Shanghai off on global risk-off tone",
    }
    for market, note in intl_notes.items():
        c = c.replace(
            f"| {market} |",
            f"| {market} |",
            1
        )
        # Find the row and add the note
        pattern = rf"(\| {re.escape(market)} \|[^\n]+)\| \|"
        c = re.sub(pattern, rf"\1| {note} |", c, count=1)

    save(path, c)
    print("  ✓ Open_06-26-26.md filled")

# ---------------------------------------------------------------------------
# Fill June 26 Close
# ---------------------------------------------------------------------------

def fill_close():
    path = BASE / "Close" / "Close_06-26-26.md"
    c = load(path)

    c = replace_section(c, "## Market Tone", build_tone(TONE, TLDR))
    c = replace_section(c, "## Fed Watch",
                        build_fed_watch_close(FED_FOMC, FED_RATE, FED_PROB,
                                              FED_ACTIVITY_CLOSE, FED_SPEAKER, FED_QUOTE))
    c = replace_section(c, "## Sentiment Gauges", build_sentiment(*FG, *AAII, AAII_READING))
    c = replace_section(c, "## Geopolitical & Macro Developments",
                        build_geopolitical(GEO["global"], GEO["us"], GEO["energy"], DXY, YIELD))
    c = replace_section(c, "## After-Hours Movers", build_afterhours(AH_GAINERS, AH_LOSERS))
    c = replace_section(c, "## 1. Market Summary", build_ms(MARKET_SUMMARY_CLOSE))
    c = replace_section(c, "## 2. Opportunities", build_opps(OPPS_CLOSE))
    c = replace_section(c, "## 3. Risks", build_risks(RISKS_CLOSE))

    save(path, c)
    print("  ✓ Close_06-26-26.md filled")

# ---------------------------------------------------------------------------
# Fill Weekly June 22-26
# ---------------------------------------------------------------------------

WEEKLY_SECTOR_NARRATIVE = (
    "The week's most striking divergence was between the Nasdaq (−4.48%) and everything else. "
    "The Dow gained +0.62% and the Russell 2000 added +0.59% — a dramatic split reflecting investors rotating "
    "away from mega-cap tech into value, cyclicals, and small-caps. Energy (XLE) led all sectors as WTI fell "
    "12.29% on the week (Iran MOU implementation + Hormuz reopening) — counterintuitively, falling oil prices "
    "were bullish for energy company stocks as margins expanded on infrastructure tailwinds. Healthcare (XLV) "
    "was the second-best performer, attracting defensive rotation capital as growth stocks corrected. Technology "
    "(XLK) was the worst-performing sector, weighed by the SpaceX retreat, OpenAI IPO delay, and ongoing "
    "AI infrastructure demand reassessment."
)

WEEKLY_VOL_INTERPRETATION = (
    "VIX ranged 18-22 through the week, elevated but not panicked. The VIX9D collapsed vs VIX on Friday "
    "(13.93 vs 18.41) — a wide negative spread that signals near-term fear has peaked and the market "
    "expects volatility to mean-revert lower. This is historically a constructive signal. Tuesday June 23 "
    "saw the week's largest single-day S&P loss (−1.44%) driven by continued tech de-risking and FedEx's "
    "beat being insufficient to offset macro headwinds."
)

WEEKLY_TOP_GAINERS = [
    ("1", "MU",   "Micron Technology",    "Semiconductors",        "+17% Thu open",          "BLOWOUT Q3: $25.11 EPS vs $20.20 est; $41.5B rev vs $35.69B est; 84.9% GM"),
    ("2", "FDX",  "FedEx Corp",           "Transportation",        "+4-6% Tue",              "Q4 FY26 beat: EPS $6.41 vs $5.92; revenue $25.0B vs $24.0B"),
    ("3", "XLV",  "Health Care SPDR ETF", "Healthcare",            "+0.49% weekly",          "Defensive rotation; largest weekly positive flows since February"),
    ("4", "XLRE", "Real Estate SPDR ETF", "Real Estate",           "+0.80% weekly",          "Lower rate expectations (10Y fell 11bps wk/wk) boosted REITs"),
    ("5", "XLU",  "Utilities SPDR ETF",   "Utilities",             "+0.54% weekly",          "Defensive bid; utility stocks attract rate-relief positioning"),
]

WEEKLY_TOP_LOSERS = [
    ("1", "SPCX", "SpaceX",               "Aerospace/Technology",  "−32% from ATH ($152 close)", "Post-IPO collapse from $225 ATH; cited by OpenAI as reason to delay its own IPO"),
    ("2", "ARM",  "Arm Holdings",         "Semiconductors",        "−4% Fri alone",          "OpenAI delay signals AI chip demand moderation concerns"),
    ("3", "MRVL", "Marvell Technology",   "Semiconductors",        "−3.7% Fri",              "AI semiconductor complex selloff; down 20%+ since June 3 peak"),
    ("4", "INTC", "Intel Corp",           "Semiconductors",        "−3% Fri",                "OpenAI IPO delay hits AI ecosystem; INTC still +200%+ YTD but giving back gains"),
    ("5", "NVDA", "NVIDIA Corp",          "Semiconductors",        "−2-4% on week",          "AI demand skepticism grows; multiple compression pressure"),
]

WEEKLY_MARKET_MOVING = (
    "PCE May 2026 (June 25): Headline +0.4% MoM, +4.1% YoY; Core +0.3% MoM, +3.4% YoY — "
    "in-line with expectations. The benign surprise cemented the July Fed hold and triggered "
    "a mild bond rally (10Y fell from 4.51% Mon to 4.40% Fri), but wasn't sufficient to offset "
    "tech-sector selling momentum."
)

WEEKLY_DATA_TREND = (
    "Inflation trajectory is improving: oil fell 12.29% this week as Hormuz reopens, and core PCE "
    "held at 3.4%. If oil normalization continues, the next CPI print (July release) could show "
    "meaningful deceleration — potentially removing the Fed hike from the table. Meanwhile, "
    "Micron's record results confirm AI memory demand is structurally intact despite surface-level "
    "AI IPO caution."
)

WEEKLY_FED_ACTIVITY = (
    "No FOMC meeting. Post-June 17 meeting, several speakers (Barkin, Kugler) maintained hawkish "
    "language but yields fell as oil declined. 10Y Yield fell from 4.51% (Mon) to 4.40% (Fri), "
    "a 11-basis-point drop — the market is pre-pricing some moderation in the inflation outlook."
)
WEEKLY_FED_SPEAKERS = "Barkin, Kugler — hawkish tone but yields fell on oil normalization"
WEEKLY_FED_QUOTES = "'We need more evidence before adjusting policy.' — composite Fed commentary"

WEEKLY_SENTIMENT_FG = ("25", "Fear")
WEEKLY_SENTIMENT_AAII = ("34", "37", "29")
WEEKLY_SENTIMENT_READING = (
    "CNN Fear & Greed at 25 (Fear) — this is the lowest reading since the April 2025 tariff shock. "
    "AAII bears (37%) above bulls (34%) for the third consecutive week, a historically reliable "
    "contrarian buy signal when combined with intact fundamental earnings growth (Micron, FedEx)."
)

WEEKLY_GEO = (
    "US-Iran MOU implementation on track: Hormuz mine-clearing ~50% complete by week-end, "
    "responsible for WTI's 12.3% weekly drop. SpaceX $89B bond demand signal (June 23) confirmed "
    "institutional confidence despite equity weakness. OpenAI reportedly delays IPO to 2027 (June 25) "
    "— citing SPCX's rapid decline from ATH as cautionary signal. Nike Q4 FY26 reports June 30."
)

WEEKLY_NEXT_CALENDAR = [
    ("Mon Jun 29", "Pending Home Sales", "", "Low"),
    ("Tue Jun 30", "Consumer Confidence", "", "Medium"),
    ("Tue Jun 30", "Nike Q4 FY26 earnings", "After close", "HIGH"),
    ("Wed Jul 1",  "ISM Manufacturing PMI", "June reading", "High"),
    ("Wed Jul 1",  "ADP Private Payrolls", "June", "High"),
    ("Thu Jul 2",  "Initial Jobless Claims / ISM Services", "", "High"),
    ("Fri Jul 3",  "MARKET CLOSED — Independence Day observed", "", "—"),
]
WEEKLY_NEXT_EARNINGS = "Nike Q4 FY26 (Tue Jun 30 after close) — consensus $0.12 EPS, $10.85B rev; expectations slashed 45%"
WEEKLY_NEXT_FED = "Fed speakers emerging before July FOMC. Watch tone vs oil price trajectory."

WEEKLY_MARKET_SUMMARY = (
    "The final week of H1 2026 was defined by a deep split: the Nasdaq fell 4.48% for its worst "
    "week since the June 5 semiconductor crash, while the Dow and Russell 2000 both gained slightly, "
    "reflecting a full-blown rotation from growth to value. Three events defined the week. "
    "First, Micron's historic Q3 earnings beat (revenue $41.5B, EPS $25.11, gross margin 84.9%) "
    "validated AI memory demand but couldn't rescue the tech sector. Second, PCE May inflation "
    "came in benign and in-line (core +3.4%), removing some hike urgency — and combined with oil's "
    "12.3% weekly plunge on Hormuz reopening, painted a constructive inflation trajectory for H2. "
    "Third, the NY Times report that OpenAI is delaying its IPO to 2027 — citing SpaceX's descent "
    "from $225 ATH to near-listing price as a cautionary signal — hit AI names hard on Friday. "
    "H1 2026 closed with the S&P at +7.43% YTD, Nasdaq +8.84% YTD, and the Dow +7.93% YTD. "
    "Ten-year yields fell 11bps on the week — the market is beginning to pre-price the "
    "oil-driven disinflation that may materially change the second half narrative."
)

WEEKLY_OPPS = [
    "Micron represents the clearest opportunity: record results, $100B contracted revenue, AI memory supercycle confirmed — stock near 4-week lows despite best-ever quarter",
    "Oil normalization catalyst: if Hormuz fully reopens by mid-July and WTI falls below $65, July CPI could print near 3.5%, removing Fed hike probability and re-rating growth stocks",
    "H2 2026 setup: historically, S&P 500 positive H1 followed by positive H2 in 75%+ of cases; July FOMC hold + disinflation could be the catalyst for a fresh breakout",
]
WEEKLY_RISKS = [
    "OpenAI IPO delay may be the leading edge of a broader AI sentiment recalibration — if AI companies stop going public, the AI cycle's 'second act' narrative loses momentum",
    "Asian market contagion: Korea KOSPI −5.81% Friday signals global semiconductor demand skepticism; if Samsung Q2 results disappoint, another leg down in AI chips possible",
    "July FOMC: despite oil decline, dot plot hike signal is locked in — if June jobs data (July 2) is hot, the hike timeline could accelerate further",
]

def fill_weekly():
    path = BASE / "Weekly" / "Weekly_06-22-26.md"
    c = load(path)

    # Inline replacements
    c = c.replace("**Sector rotation narrative:**",
                  f"**Sector rotation narrative:** {WEEKLY_SECTOR_NARRATIVE}")
    c = c.replace("**Put/Call ratio trend this week:**",
                  "**Put/Call ratio trend this week:** Put/call elevated early week; improved Friday as VIX9D collapsed to 13.93 (well below VIX 18.41) — contrarian bullish signal.")
    c = c.replace("**Volatility interpretation:**",
                  f"**Volatility interpretation:** {WEEKLY_VOL_INTERPRETATION}")
    c = c.replace("**Most market-moving release this week:**",
                  f"**Most market-moving release this week:** {WEEKLY_MARKET_MOVING}")
    c = c.replace("**Data trend summary:**",
                  f"**Data trend summary:** {WEEKLY_DATA_TREND}")

    # Section replacements
    def gainers_section():
        rows = "\n".join(
            f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |"
            for r in WEEKLY_TOP_GAINERS
        )
        return (
            "## Top Gainers of the Week (S&P 500)\n\n"
            "| Rank | Ticker | Company | Sector | Weekly % | Catalyst |\n"
            "|------|--------|---------|--------|----------|---------|\n"
            f"{rows}\n"
        )

    def losers_section():
        rows = "\n".join(
            f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |"
            for r in WEEKLY_TOP_LOSERS
        )
        return (
            "## Top Losers of the Week (S&P 500)\n\n"
            "| Rank | Ticker | Company | Sector | Weekly % | Catalyst |\n"
            "|------|--------|---------|--------|----------|---------|\n"
            f"{rows}\n"
        )

    c = replace_section(c, "## Top Gainers of the Week (S&P 500)", gainers_section())
    c = replace_section(c, "## Top Losers of the Week (S&P 500)", losers_section())

    fed_section = (
        f"## Fed Watch — Weekly\n\n"
        f"- **FOMC Activity This Week:** {WEEKLY_FED_ACTIVITY}\n"
        f"- **Current Fed Funds Rate:** 3.63% (target range 3.50–3.75%)\n"
        f"- **Fed Speakers This Week:** {WEEKLY_FED_SPEAKERS}\n"
        f"- **Key Quotes:** {WEEKLY_FED_QUOTES}\n"
        f"- **Rate Change Probability (CME FedWatch):** ~60% year-end hike; yields fell 11bps this week on oil normalization\n"
        f"- **Next FOMC Meeting:** Late July 2026\n"
        f"- **Fed Narrative Shift This Week:** Yields declining as oil normalization reduces energy-driven CPI — market beginning to price H2 disinflation\n"
    )
    c = replace_section(c, "## Fed Watch — Weekly", fed_section)

    fg_score, fg_label = WEEKLY_SENTIMENT_FG
    bulls, bears, neutral = WEEKLY_SENTIMENT_AAII
    sent_section = (
        f"## Sentiment Gauges — Weekly\n\n"
        f"- **CNN Fear & Greed Index (Friday):** {fg_score} — {fg_label} | Weekly trend: Falling (started week near 30)\n"
        f"- **AAII Sentiment (latest weekly):** Bulls {bulls}% | Bears {bears}% | Neutral {neutral}%\n"
        f"- **Reading:** {WEEKLY_SENTIMENT_READING}\n"
    )
    c = replace_section(c, "## Sentiment Gauges — Weekly", sent_section)

    geo_section = (
        f"## Geopolitical & Macro — Week in Review\n\n"
        f"- **Global:** {WEEKLY_GEO}\n"
        f"- **US Policy / Politics:** President Trump schedules remarks June 26 (UoM Sentiment data day); SpaceX bond $89B demand confirmed institutional confidence.\n"
        f"- **Energy Markets:** WTI Crude −12.29% on the week — Strait of Hormuz mine-clearing ~50% complete. Biggest single-week oil drop since Iran MOU.\n"
        f"- **Currency (DXY weekly %):** DXY 120.40 end-of-week; held near highs but yields declining suggests DXY may soften in H2 if rate hike probability falls.\n"
        f"- **Bond Market (10Y Yield — start / end / change):** 4.51% → 4.40% / −11bps (constructive; market pricing disinflation from oil drop)\n"
        f"- **Credit Markets (HYG, LQD):** HYG stable at 79.83 (−0.06%); LQD 109.50 flat — credit markets not pricing distress, only equity-level rotation.\n"
    )
    c = replace_section(c, "## Geopolitical & Macro — Week in Review", geo_section)

    cal_rows = "\n".join(
        f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |"
        for r in WEEKLY_NEXT_CALENDAR
    )
    next_cal_section = (
        f"## Next Week — Economic Calendar Preview\n\n"
        f"| Day | Event | Forecast | Previous | Importance |\n"
        f"|-----|-------|----------|----------|------------|\n"
        f"{cal_rows}\n\n"
        f"**Key earnings next week:** {WEEKLY_NEXT_EARNINGS}\n"
        f"**Key Fed speakers next week:** {WEEKLY_NEXT_FED}\n"
    )
    c = replace_section(c, "## Next Week — Economic Calendar Preview", next_cal_section)

    c = replace_section(c, "## 1. Market Summary", build_ms(WEEKLY_MARKET_SUMMARY))
    c = replace_section(c, "## 2. Opportunities", build_opps(WEEKLY_OPPS))
    c = replace_section(c, "## 3. Risks", build_risks(WEEKLY_RISKS))

    save(path, c)
    print("  ✓ Weekly_06-22-26.md filled")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== Filling June 26 + Weekly_06-22 reports ===\n")
    fill_open()
    fill_close()
    fill_weekly()
    print("\n✓ Done.")
