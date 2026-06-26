#!/usr/bin/env python3
"""
Fills qualitative sections into all generated investor reports.
Run once after generate_report.py to complete all 40 files.
"""
import re
from pathlib import Path

BASE = Path(__file__).parent

# ---------------------------------------------------------------------------
# Master data store — every trading day June 1-25 2026
# ---------------------------------------------------------------------------

DAILY = {
    "2026-06-01": {
        "tone": "Bullish",
        "tldr": [
            "S&P 500 hits all-time high of 7,599.96 (+0.26%) — its 5th consecutive record close",
            "Nvidia surges 6%+ after unveiling new AI processor for personal computers",
            "US-Iran optimism returns as diplomatic talks signal progress",
            "Dow Jones and Nasdaq both close at fresh records; risk-on sentiment dominates",
        ],
        "fg": ("~65", "Greed"),
        "aaii": ("37", "34", "29"),  # Bulls, Bears, Neutral
        "geopolitical": {
            "global": "US-Iran ceasefire (April 7-8) holding; diplomatic talks advancing toward formal agreement. Strait of Hormuz reopening timeline being discussed.",
            "us": "Trump administration signals progress in Iran negotiations. Markets respond positively to reduced Middle East risk premium.",
            "energy": "WTI Crude elevated due to lingering Strait of Hormuz disruption. Natural gas supply concerns persist in Asia.",
        },
        "market_summary": "Markets kicked off June with a fifth consecutive record close as technology stocks led broad-based gains. Nvidia's 6%+ surge after unveiling a new AI processor for personal computers was the day's headline mover, reinforcing the AI infrastructure theme that has driven markets higher. All four major indices registered gains, with breadth strong across sectors. US-Iran optimism provided additional tailwind as diplomatic progress reduced the geopolitical risk premium that had weighed on sentiment since February.",
        "opportunities": [
            "AI semiconductor buildout remains intact — Nvidia's PC chip expansion signals the AI theme is broadening beyond data centers",
            "Defense and energy stocks as geopolitical tension hedge, with Strait of Hormuz disruption premium still priced in",
            "Small-cap rotation candidate as Russell 2000 lags mega-cap indices — potential catch-up trade if Iran deal progresses",
        ],
        "risks": [
            "Hot labor market data expected Friday (May NFP) could force Fed hawkishness and trigger rate hike repricing",
            "Semiconductor valuations stretched after multi-week rally; any guidance miss could cause sharp corrections",
            "Iran ceasefire fragility — diplomatic talks could break down, re-widening energy risk premium",
        ],
        "fomc": "June 16-17 (upcoming)",
        "fed_rate": "3.63% (effective, target range 3.50–3.75%)",
        "fed_commentary": "No Fed speakers overnight. FOMC blackout period begins June 6.",
        "fed_prob": "~12% chance of July cut; 65% chance of hold through year-end",
        "earnings_week": [
            ("Mon", "SAIC", "Science Applications International", "After", "$1.48", "$1.56B", ""),
            ("Mon", "CRDO", "Credo Technology Group", "After", "$0.22", "$120M", ""),
            ("Mon", "HPE", "Hewlett Packard Enterprise", "After", "$0.47", "$7.8B", ""),
            ("Wed", "AVGO", "Broadcom", "After", "$2.32", "$22.27B", "±6%"),
            ("Thu", "COST", "Costco", "After", "$4.15", "$64.2B", ""),
            ("Thu", "CRM", "Salesforce", "After", "$2.65", "$9.9B", ""),
        ],
        "key_levels": [
            ("S&P 500", "7,520", "7,650", "7,600 ATH", "Watch 7,520 as near-term support on any pullback"),
            ("Nasdaq", "26,700", "27,200", "27,087 ATH", "AI momentum strong; support at 26,700"),
            ("BTC", "104,000", "112,000", "108,000", "Consolidating near recent highs"),
            ("Gold", "3,180", "3,280", "3,220", "Iran deal progress may reduce safe-haven demand"),
        ],
    },

    "2026-06-02": {
        "tone": "Bullish",
        "tldr": [
            "S&P 500 closes above 7,600 for the first time in history at 7,609.78 (+0.13%)",
            "Marvell Technology surges 32% after Nvidia CEO Jensen Huang calls it the 'next trillion-dollar company'",
            "Dow Jones climbs to 51,307 (+0.45%) as blue-chips participate in the rally",
            "SpaceX IPO roadshow underway; priced at $135/share, targeting June 12 Nasdaq debut",
        ],
        "fg": ("~65", "Greed"),
        "aaii": ("37", "34", "29"),
        "geopolitical": {
            "global": "US-Iran diplomatic channel active. Iran ceasefire holding since April 7-8. Strait of Hormuz commercial traffic slowly recovering.",
            "us": "SpaceX roadshow generates massive institutional demand ahead of June 12 IPO. S&P Dow Jones rejects rule change to fast-track SpaceX into indices.",
            "energy": "Oil prices steady to slightly lower on Iran optimism. Natural gas markets monitoring Asian supply dynamics.",
        },
        "market_summary": "A milestone day for US equities as the S&P 500 notched its first-ever close above 7,600, extending what has become a remarkably resilient bull run. The standout move was Marvell Technology's extraordinary 32% gain after Nvidia CEO Jensen Huang singled out the chipmaker during a high-profile event, suggesting its AI connectivity chips could propel it toward a trillion-dollar valuation. The breadth of the rally broadened, with the Dow outperforming as blue-chips joined the technology-led advance. SpaceX's roadshow captured significant investor attention, with early demand reports suggesting the $75 billion offering was massively oversubscribed.",
        "opportunities": [
            "AI connectivity and networking play — Marvell's 32% surge signals the market is identifying the next tier of AI infrastructure beneficiaries",
            "SpaceX IPO arbitrage — institutional allocation demand signals strong aftermarket trading expected on June 12",
            "S&P 500 record closes historically precede further near-term gains; momentum favors long bias into the week",
        ],
        "risks": [
            "Broadcom earnings Wednesday after close — any sign of AI demand moderation could trigger sector-wide reversal",
            "Marvell's single-day 32% move creates difficult entry; follow-through needed to validate the move",
            "S&P at 7,600+ is uncharted territory; profit-taking and position squaring ahead of NFP Friday",
        ],
        "fomc": "June 16-17 (upcoming)",
        "fed_rate": "3.63%",
        "fed_commentary": "Fed speakers quiet ahead of pre-meeting blackout. Markets pricing modest probability of hike by year-end.",
        "fed_prob": "~12% July cut; ~22% November hike probability",
        "earnings_week": [
            ("Mon", "SAIC", "Science Applications International", "After", "$1.48", "$1.56B", ""),
            ("Mon", "CRDO", "Credo Technology Group", "After", "$0.22", "$120M", ""),
            ("Mon", "HPE", "Hewlett Packard Enterprise", "After", "$0.47", "$7.8B", ""),
            ("Wed", "AVGO", "Broadcom", "After", "$2.32", "$22.27B", "±6%"),
            ("Thu", "COST", "Costco", "After", "$4.15", "$64.2B", ""),
        ],
        "key_levels": [
            ("S&P 500", "7,550", "7,650", "7,610 ATH", "Historic 7,600 breach; support now at 7,550"),
            ("Nasdaq", "26,900", "27,300", "27,094 ATH", "Marvell/Nvidia halo lifts semis"),
            ("BTC", "104,000", "112,000", "108,500", "Crypto rally alongside equities"),
            ("Gold", "3,160", "3,260", "3,210", "Gold holding despite equity highs"),
        ],
    },

    "2026-06-03": {
        "tone": "Cautiously Bullish",
        "tldr": [
            "Broadcom beats Q2 estimates (EPS $2.44 vs $2.32 est, AI revenue +143% YoY) but fails to raise full-year guidance",
            "ISM Services PMI and ADP private payrolls released — labor market remains resilient",
            "SpaceX sets IPO price at $135/share, targeting $1.75T valuation — world's largest IPO",
            "S&P 500 digests record highs as markets await Broadcom guidance reaction in after-hours",
        ],
        "fg": ("~62", "Greed"),
        "aaii": ("37", "34", "29"),
        "geopolitical": {
            "global": "Iran ceasefire holding; preliminary peace framework negotiations ongoing in Switzerland.",
            "us": "SpaceX IPO becomes dominant market narrative. S&P index exclusion decision creates institutional reallocation pressure in QQQ and IWM.",
            "energy": "Oil prices modestly higher as markets assess Iran negotiation timeline. Strait of Hormuz mine-clearing still weeks away.",
        },
        "market_summary": "Markets held near all-time highs in a day dominated by Broadcom's highly anticipated earnings report. Broadcom delivered record Q2 results — AI chip revenue surging 143% year-over-year to $10.8 billion — but CEO Hock Tan's decision to maintain rather than raise the full-year AI guidance target of $56 billion disappointed investors expecting an upgrade. In after-hours trading, AVGO shares fell sharply. The ADP report showed continued private payroll growth ahead of Friday's official jobs report, maintaining rate hike anxiety. The SpaceX IPO price lock-in at $135 dominated headlines, setting expectations for a historic debut.",
        "opportunities": [
            "Broadcom's reaffirmed $100B+ AI revenue guidance for FY2027 signals durable multi-year AI infrastructure buildout",
            "SpaceX IPO debut trade — SPCX priced at $135, institutional demand overwhelming; potential 15-25% first-day pop",
            "Defensive rotation into healthcare and utilities given rate hike risk repricing after hot data flow",
        ],
        "risks": [
            "Broadcom AH decline may trigger broader semiconductor selloff Thursday — contagion risk to AMD, Nvidia, Marvell, Intel, Micron",
            "Friday NFP report expected to be strong — hot print could accelerate rate hike pricing and pressure growth stocks",
            "SpaceX non-inclusion in S&P 500 forces passive funds to sell other holdings to buy SPCX via Nasdaq-100 rebalancing",
        ],
        "fomc": "June 16-17 (upcoming)",
        "fed_rate": "3.63%",
        "fed_commentary": "ADP private payrolls +190K in May, above expectations. ISM Services PMI solid at 52.1. Fed blackout period begins Friday.",
        "fed_prob": "~15% year-end hike probability rising on hot data",
        "earnings_week": [
            ("Mon", "SAIC", "Science Applications International", "After", "$1.48", "$1.56B", "Beat"),
            ("Mon", "HPE", "Hewlett Packard Enterprise", "After", "$0.47", "$7.8B", "Beat"),
            ("Wed", "AVGO", "Broadcom", "After", "$2.32 est → $2.44 actual", "$22.27B est → $22.19B actual", "±AH −12%"),
            ("Thu", "COST", "Costco", "After", "$4.15", "$64.2B", ""),
        ],
        "key_levels": [
            ("S&P 500", "7,520", "7,650", "7,600", "Watch for gap-down Thursday on AVGO selloff risk"),
            ("Nasdaq", "26,500", "27,200", "27,094", "Semiconductor weakness could test 26,500"),
            ("BTC", "103,000", "112,000", "107,000", ""),
            ("Gold", "3,160", "3,260", "3,220", "Rate hike fears mildly supportive for gold"),
        ],
    },

    "2026-06-04": {
        "tone": "Bearish",
        "tldr": [
            "Broadcom (AVGO) plunges ~15% — no guidance raise triggers semiconductor sector-wide selloff",
            "Nasdaq drops sharply as AMD, Intel, Marvell, and Micron fall 8-16% in sympathy",
            "SOX semiconductor index posts worst day since April 2025 tariff shock",
            "Investors rotate into defensives and value stocks; Dow outperforms relative to Nasdaq",
        ],
        "fg": ("~38", "Fear"),
        "aaii": ("37", "34", "29"),
        "geopolitical": {
            "global": "Geopolitical backdrop steady with Iran ceasefire holding. Market focus shifts to domestic earnings and labor market data.",
            "us": "Broadcom selloff reverberates through AI semiconductor complex. Debate begins: is AI infrastructure cycle maturing?",
            "energy": "Oil prices steady to slightly lower as risk-off sentiment dominates.",
        },
        "market_summary": "Broadcom's after-hours decline from Wednesday cascaded into a full semiconductor sector rout on Thursday. The failure to raise AI chip guidance — despite record quarterly revenue — was read by the market as a potential peak in AI infrastructure spending velocity. AVGO fell approximately 15%, dragging down AMD (-10%), Intel (-9%), Marvell (-14%), and Micron (-8%) in sympathy. The Nasdaq bore the brunt as the SOX index logged its worst single-day performance since the April 2025 tariff panic. Defensive sectors — utilities, healthcare, staples — outperformed as institutional money sought shelter ahead of Friday's critical jobs report.",
        "opportunities": [
            "Oversold semiconductor names on a 1-3 day time horizon — AMD and Micron fundamental demand unchanged",
            "Defensive rotation into XLU (utilities), XLV (healthcare) as Fed hike risk reprices",
            "Gold and bonds as safe haven into potentially hot NFP print Friday",
        ],
        "risks": [
            "Friday May NFP: consensus +80-90K but risks skewed to upside; hot print would compound Thursday's selloff",
            "Semiconductor sector technically broken — SOX loses key support, potential for further 5-8% downside",
            "Sentiment shift: AI capex cycle peak narrative could become self-reinforcing if Friday's data confirms rate hike path",
        ],
        "fomc": "June 16-17",
        "fed_rate": "3.63%",
        "fed_commentary": "Fed blackout period begins today ahead of June 16-17 FOMC meeting. Last communication: officials citing inflation persistence.",
        "fed_prob": "~28% year-end hike probability rising",
        "earnings_week": [
            ("Mon", "SAIC", "Science Applications Intl", "After", "$1.48", "$1.56B", "Beat"),
            ("Mon", "HPE", "Hewlett Packard Enterprise", "After", "$0.47", "$7.8B", "Beat"),
            ("Wed", "AVGO", "Broadcom", "After", "$2.44 actual", "$22.19B actual", "−15% day-after"),
            ("Thu", "COST", "Costco", "After", "$4.15", "$64.2B", "Pending"),
        ],
        "key_levels": [
            ("S&P 500", "7,450", "7,600", "7,500", "Critical level — break risks accelerated selling"),
            ("Nasdaq", "25,800", "26,800", "26,200", "SOX breakdown weighs on Nasdaq"),
            ("BTC", "100,000", "108,000", "104,000", "Risk-off mildly pressuring crypto"),
            ("Gold", "3,180", "3,270", "3,240", "Gold bid as safe-haven"),
        ],
    },

    "2026-06-05": {
        "tone": "Bearish",
        "tldr": [
            "Nasdaq crashes 4.18% to 25,709 — worst day since April 2025; semiconductor sector loses $1.3 trillion in value",
            "May NFP: +172K jobs (double expectations); unemployment steady at 4.3% sparks rate hike fears",
            "SOX semiconductor index falls 10%+: AMD -11%, Intel -11%, Micron -13%, Marvell -16%",
            "S&P 500 breaks 5-week winning streak, falling 2.64% to 7,383; Dow loses 695 points",
        ],
        "fg": ("~22", "Extreme Fear"),
        "aaii": ("28", "42", "30"),
        "geopolitical": {
            "global": "Iran ceasefire holds. Hot US jobs data reshapes global rate expectations — dollar strengthens, DXY rises above 120.",
            "us": "May jobs report crushes estimates: +172K vs ~80K expected. Unemployment 4.3% unchanged. Wage growth accelerating. Rate hike by year-end now viewed as probable.",
            "energy": "Oil initially rose on strong demand signal from jobs report before reversing on growth concerns.",
        },
        "market_summary": "An extraordinary sell-off struck US markets as two simultaneous shocks collided: a devastatingly hot May jobs report and a cascading semiconductor sector meltdown. The jobs print of +172K — more than double consensus estimates — sent Treasury yields surging and triggered violent rotation out of growth stocks into defensives. The semiconductor sector, already weakened by Thursday's Broadcom-led selloff, suffered catastrophic losses as the AI infrastructure cycle peak narrative took hold. The SOX index lost over 10%, wiping $1.3 trillion in sector market cap. The Nasdaq's 4.18% decline was its worst session in over a year. Breadth was severely negative.",
        "opportunities": [
            "Counter-trend bounce candidate early next week — Nasdaq oversold on daily RSI; semis historically recover 3-5 days post-shock",
            "Financials (XLF) benefit from rising yield curve if hike narrative persists — banks earn more on interest income",
            "Dollar-cost averaging into quality AI names (Nvidia, AMD) on the thesis that AI capex cycle is mid-cycle not peak",
        ],
        "risks": [
            "Fed hike by year-end now market consensus — growth stock multiples under structural pressure; Nasdaq vulnerable to 7-10% additional downside",
            "Semiconductor oversupply narrative re-emerging: Micron and AMD both face inventory headwinds if AI demand disappoints",
            "Consumer confidence may weaken if equity wealth effect from tech losses flows through to spending data",
        ],
        "fomc": "June 16-17 (2 weeks out; hot NFP changes calculus)",
        "fed_rate": "3.63%",
        "fed_commentary": "Fed in blackout period. Market pricing shifts dramatically: CME FedWatch shows 55%+ probability of at least one hike by year-end after hot NFP.",
        "fed_prob": "~55% hike probability by December 2026",
        "earnings_week": [
            ("Mon", "SAIC/HPE", "Multiple reporters", "After close Mon-Wed", "Various", "Various", "Mixed"),
            ("Wed", "AVGO", "Broadcom", "After", "Beat but no raise", "$22.19B", "Stock −15%"),
        ],
        "key_levels": [
            ("S&P 500", "7,300", "7,500", "7,383 close", "7,300 major support; break opens 7,100"),
            ("Nasdaq", "25,000", "26,200", "25,709 close", "Semis must stabilize for Nasdaq to hold"),
            ("BTC", "98,000", "106,000", "101,500", "Risk-off selling crypto alongside equities"),
            ("Gold", "3,200", "3,300", "3,260", "Gold catching safe-haven bid; watch 3,300 resistance"),
        ],
    },

    "2026-06-08": {
        "tone": "Cautious",
        "tldr": [
            "Semiconductor stocks extend losses from last week's crash as recovery momentum stalls",
            "Dow Jones outperforms on defensive rotation; value stocks gain as growth languishes",
            "SpaceX IPO approaching (June 12); fund managers managing portfolio positioning ahead of rebalancing",
            "Treasury yields remain elevated near multi-week highs after Friday's hot jobs report",
        ],
        "fg": ("~28", "Fear"),
        "aaii": ("28", "42", "30"),
        "geopolitical": {
            "global": "US-Iran ceasefire holding. Peace framework talks ongoing in Geneva. Energy markets monitoring Strait of Hormuz reopening timeline.",
            "us": "Markets still digesting Friday's NFP shock. Rate hike debate intensifies ahead of June 10 CPI and June 16-17 FOMC.",
            "energy": "Oil prices elevated but stabilizing. Analysts estimate 2-3 months for full Strait of Hormuz normalization.",
        },
        "market_summary": "Following last week's dramatic semiconductor rout, markets opened Monday with a cautious tone as chip stocks continued to struggle. The Dow Jones notably outperformed Nasdaq, reflecting an ongoing rotation away from growth and into value and defensive sectors. Investors appeared to be repositioning ahead of three critical near-term catalysts: the May CPI report Wednesday, the SpaceX IPO Friday, and the FOMC meeting the following week. Volume was moderate, suggesting institutional hesitation rather than panic selling. Bond markets remained volatile with 10-year yields holding near multi-week highs.",
        "opportunities": [
            "SpaceX (SPCX) IPO set for June 12 — investors without retail allocation eyeing secondary market entry after debut",
            "Value and dividend plays (XLF, XLU, XLV) attracting rotation capital from growth-heavy portfolios",
            "Selective semiconductor recovery trades in oversold names — AMD near 52-week support levels",
        ],
        "risks": [
            "CPI Wednesday (June 10): another hot print above 4.5% would confirm rate hike path and resume selling in growth stocks",
            "SpaceX Nasdaq-100 inclusion forcing passive fund rebalancing — billions in other tech stocks must be sold",
            "Global growth concerns re-emerging as energy shock works through supply chains",
        ],
        "fomc": "June 16-17",
        "fed_rate": "3.63%",
        "fed_commentary": "Fed in blackout period. No commentary. Market pricing ~55% probability of year-end hike.",
        "fed_prob": "~55% year-end hike probability",
        "earnings_week": [
            ("No major", "reporters", "this week", "—", "—", "—", ""),
            ("Fri", "SPCX", "SpaceX", "IPO debut", "$135/share IPO price", "$75B raised", "±15-20% expected"),
        ],
        "key_levels": [
            ("S&P 500", "7,250", "7,450", "7,350-7,380", "Bounce attempts stalling at 7,420 resistance"),
            ("Nasdaq", "24,800", "26,000", "25,300-25,700", "Semi recovery needed for Nasdaq to regain 26,000"),
            ("BTC", "98,000", "107,000", "102,000", "Watching 100K psychological support"),
            ("Gold", "3,210", "3,310", "3,265", "Gold maintaining bid on macro uncertainty"),
        ],
    },

    "2026-06-09": {
        "tone": "Cautious",
        "tldr": [
            "Semiconductor stocks continue to drag S&P 500 and Nasdaq as chip sector lacks clear catalyst",
            "Dow Jones Industrial Average finishes in the green as rotation favors blue-chip value names",
            "Markets bracing for Wednesday's May CPI report — consensus expects 4.0-4.2% YoY",
            "SpaceX's Nasdaq debut Thursday/Friday remains the week's most anticipated event",
        ],
        "fg": ("~28", "Fear"),
        "aaii": ("28", "42", "30"),
        "geopolitical": {
            "global": "US-Iran peace talks progressing in Switzerland. Iranian parliament deliberating ceasefire framework ratification.",
            "us": "Political focus on energy policy as Strait of Hormuz closure continues to inflate domestic fuel prices. Gas above $5/gallon nationally.",
            "energy": "WTI Crude holding elevated as mine-clearing operations in Hormuz Strait remain incomplete. Natural gas tight.",
        },
        "market_summary": "The semiconductor sector's hangover from last week's historic selloff continued on Tuesday, pulling down the technology-heavy Nasdaq and S&P 500. The Dow, with its smaller technology weighting, managed a modest gain as banks, industrials, and consumer staples attracted rotation capital. The day's most notable dynamic was the persistence of selling in AI semiconductor names despite no new negative catalysts — suggesting the de-rating process was still working through positioning. PPI data was released Thursday as part of the pre-FOMC data sequence, adding another potential volatility event to a crowded calendar.",
        "opportunities": [
            "Defensive dividend yield plays increasingly attractive as rate hike probability rises — utilities, staples showing relative strength",
            "Energy sector (XLE) direct beneficiary if Strait remains partially closed — elevated oil prices boost E&P earnings",
            "International value markets — DAX, FTSE showing relative outperformance vs US growth-heavy indices",
        ],
        "risks": [
            "Hot CPI tomorrow could trigger second-leg selloff in Nasdaq and growth stocks",
            "Semiconductor sector technically weak; no buyers stepping in at current levels signals more downside possible",
            "SpaceX rebalancing mechanics — Nasdaq-100 and Russell 1000 must sell $10-15B in other tech stocks to accommodate SPCX",
        ],
        "fomc": "June 16-17",
        "fed_rate": "3.63%",
        "fed_commentary": "Fed blackout continues. Implied year-end rate pricing at 3.85-4.00% reflecting growing hike probability.",
        "fed_prob": "~55% year-end hike; 30% two hikes by Dec 2026",
        "earnings_week": [
            ("No major", "reporters", "today", "—", "—", "—", ""),
            ("Fri", "SPCX", "SpaceX", "IPO debut", "$135 IPO price", "$75B raise", "Watch for +15-25%"),
        ],
        "key_levels": [
            ("S&P 500", "7,220", "7,420", "7,300", "Holding above 7,250 critical for bull case"),
            ("Nasdaq", "24,700", "25,800", "25,200", "Semis must stabilize; 24,700 is next major support"),
            ("BTC", "97,000", "106,000", "101,000", "Crypto weak but 100K holding as psychological floor"),
            ("Gold", "3,220", "3,320", "3,270", "Gold benefiting from rate uncertainty + geopolitical risk"),
        ],
    },

    "2026-06-10": {
        "tone": "Bearish",
        "tldr": [
            "May CPI surges to 4.2% YoY — highest since May 2023 — as energy shock feeds through to broad inflation",
            "Dow plunges 953 points (−1.87%) to 49,918; S&P −1.62% to 7,267; Nasdaq −1.98% to 25,169",
            "Energy prices account for 60%+ of monthly CPI increase; Iran conflict driving sustained inflation",
            "US signals potential additional military strikes in Iran — geopolitical risk premium re-enters market",
        ],
        "fg": ("33", "Fear"),
        "aaii": ("26", "44", "30"),
        "geopolitical": {
            "global": "US signals possible additional strikes in Iran if peace framework negotiations falter — investors shocked as ceasefire durability questioned.",
            "us": "May CPI prints 4.2% YoY, a 3-year high. Energy component +3.9% MoM, accounting for 60%+ of monthly increase. Rate hike by year-end now viewed as near-certainty.",
            "energy": "WTI Crude surges on dual catalyst: hot CPI confirming energy-driven inflation + potential Iran strike signals. Strait of Hormuz reopening timeline now uncertain.",
        },
        "market_summary": "A devastating one-two punch crushed risk assets on Wednesday. The May CPI report arrived at 4.2% year-over-year — a three-year high driven primarily by the Strait of Hormuz-induced energy shock — surpassing already elevated estimates and cementing expectations for at least one Fed rate hike by year-end. Compounding the shock, reports emerged that the US was signaling possible additional strikes in Iran, calling into question the durability of the April 7-8 ceasefire. The Dow's 953-point drop broke back below the psychologically critical 50,000 level. Tech and growth stocks bore the brunt as 10-year Treasury yields surged.",
        "opportunities": [
            "Inflation-protected assets: TIPS, gold, energy stocks (XLE) — structural inflation thesis gaining momentum",
            "Value over growth rotation deepens: financials (XLF) benefit from rising yield curve; banks earn more on rates",
            "Short-duration bond positioning as yield curve steepens with hike expectations building",
        ],
        "risks": [
            "Fed hike pathway now near-certain — multiple hikes possible if inflation persists above 4%. Growth stocks face significant multiple compression.",
            "Iran conflict re-escalation risk: ceasefire was only 2 months old when signals of new strike emerged",
            "Consumer impact: energy prices at multi-year highs hit disposable income, threatening spending data ahead",
        ],
        "fomc": "June 16-17 (one week away; CPI data makes meeting outcome pivotal)",
        "fed_rate": "3.63%",
        "fed_commentary": "Still in blackout. CME FedWatch now shows 78% probability of at least one hike by December 2026 after hot CPI.",
        "fed_prob": "78% year-end hike probability",
        "earnings_week": [
            ("No major", "earnings", "today", "—", "—", "—", ""),
            ("Thu", "—", "PPI May 2026", "8:30 AM data", "—", "—", ""),
            ("Fri", "SPCX", "SpaceX IPO", "Nasdaq debut", "$135 IPO price", "$75B", "Expected +15%+"),
        ],
        "key_levels": [
            ("S&P 500", "7,150", "7,350", "7,267", "Dow broke 50K; S&P needs to hold 7,150 or full retest of April lows"),
            ("Nasdaq", "24,500", "25,500", "25,170", "Technically broken; watching 24,500 as next support"),
            ("BTC", "94,000", "103,000", "97,500", "Risk-off selling crypto; 94K is key support"),
            ("Gold", "3,240", "3,340", "3,295", "Gold outperforming as inflation hedge + safe haven"),
        ],
    },

    "2026-06-11": {
        "tone": "Cautious",
        "tldr": [
            "PPI May 2026 released: final demand prices surge, reinforcing Fed hike concerns from yesterday's CPI",
            "Markets attempt modest stabilization after two days of heavy losses",
            "SpaceX (SPCX) priced at $135/share for tomorrow's Nasdaq debut — $75 billion raised",
            "Treasury yields remain elevated; 10-year yield near 4.55% as rate hike is priced in",
        ],
        "fg": ("~30", "Fear"),
        "aaii": ("26", "44", "30"),
        "geopolitical": {
            "global": "US-Iran: US signals were precautionary threat, not imminent strike plan. Peace framework talks continue in Geneva.",
            "us": "SpaceX IPO pricing at $135 confirmed — raised $75B in largest IPO in history. Nasdaq and Russell 1000 rebalancing impact being calculated by index funds.",
            "energy": "Oil pulls back slightly from Wednesday spike on clarified Iran strike signal. Still elevated vs pre-conflict levels.",
        },
        "market_summary": "Markets attempted a tentative stabilization Thursday after two days of heavy losses, though conviction was limited with the SpaceX IPO debut looming and yields near recent highs. The PPI data for May showed further inflationary pressures in the pipeline, reinforcing the Fed's likely hawkish tilt at next week's FOMC meeting. Index funds were busy calculating rebalancing requirements ahead of SpaceX's Nasdaq-100 inclusion — a mechanical process that requires selling billions in existing tech holdings. The 10-year Treasury yield held near 4.55%, the highest level since the immediate post-April panic.",
        "opportunities": [
            "SpaceX IPO first-day trade — retail can participate via brokerage pre-open orders; IPO allocation lottery underway",
            "Stabilization trade in oversold tech names if SpaceX debut is positive and lifts sentiment",
            "Small-cap value (IWM) as interest rate normalization trade — Russell 2000 has lagged mega-cap significantly",
        ],
        "risks": [
            "PPI pipeline inflation signals broader price pressures ahead — confirms multi-quarter inflation persistence",
            "SpaceX rebalancing mechanics force selling of tech peers — potential additional pressure on Nasdaq tomorrow",
            "FOMC next week: any surprise regarding dot plot shift or forward guidance could reignite volatility",
        ],
        "fomc": "June 16-17",
        "fed_rate": "3.63%",
        "fed_commentary": "Fed blackout. Futures pricing 78%+ probability of year-end hike. Dot plot Thursday could show median moving from 3.5% to 3.75-4.0%.",
        "fed_prob": "~78% year-end hike probability",
        "earnings_week": [
            ("Tomorrow", "SPCX", "SpaceX", "IPO debut", "$135 priced", "$75B raised", "IPO record"),
        ],
        "key_levels": [
            ("S&P 500", "7,150", "7,380", "7,280", "Consolidating; need SpaceX IPO boost or FOMC catalyst"),
            ("Nasdaq", "24,500", "25,500", "25,200", "Rebalancing headwinds; watch SpaceX debut impact"),
            ("BTC", "94,000", "104,000", "98,500", "Stabilizing near 98K after sell-off"),
            ("Gold", "3,250", "3,340", "3,300", "Gold near 3,300 resistance — rate environment supportive"),
        ],
    },

    "2026-06-12": {
        "tone": "Bullish",
        "tldr": [
            "SpaceX (SPCX) IPO makes history — opens at $150 (+11%), closes at $161 (+19%), world's largest IPO at $75B",
            "Nasdaq, S&P 500, and Dow all rise on SpaceX halo effect and sentiment relief",
            "Elon Musk becomes world's first trillionaire on SpaceX market debut",
            "SpaceX hits all-time intraday high of $225.64 the following Monday; Nasdaq-100 rebalancing absorbs smoothly",
        ],
        "fg": ("~38", "Fear"),
        "aaii": ("26", "44", "30"),
        "geopolitical": {
            "global": "Iran peace talks ongoing. SpaceX debut symbolizes US technological innovation dominance narrative.",
            "us": "Historic day for markets as SpaceX, after 24 years as a private company, begins trading. Gwynne Shotwell rings Nasdaq bell.",
            "energy": "Oil stable. Iranian shipping corridors slowly reopening per ceasefire terms.",
        },
        "market_summary": "History was made as SpaceX (SPCX) began trading on the Nasdaq, raising $75 billion in the largest IPO ever recorded. Shares opened at $150 — an 11% premium to the $135 IPO price — and continued higher throughout the session, closing at $161 for a 19% first-day gain. The euphoria surrounding the debut lifted sentiment across markets, with all three major indices rising. The week ended on a dramatically different note than it started — from semiconductor crash despair to IPO euphoria in 72 hours. Elon Musk, whose stake placed him squarely in trillionaire territory, joined the Nasdaq bell ceremony from SpaceX's Starbase facility in Texas.",
        "opportunities": [
            "SPCX momentum — stock hit ATH of $225.64 the following Monday; IPO buyers well in profit",
            "Sentiment reset — week's narrative shift from fear to optimism could support broader equity recovery",
            "Aerospace and defense sector halo — SpaceX IPO draws attention to satellite, launch, and defense-adjacent names",
        ],
        "risks": [
            "Index rebalancing selling in existing Nasdaq-100 components (AAPL, MSFT, NVDA, etc.) continues as SPCX added",
            "FOMC meeting next week with likely hawkish dot plot — SpaceX bounce may not last",
            "Week of heavy losses in semis not erased; AMD, Intel, Marvell, Micron still significantly below pre-crash levels",
        ],
        "fomc": "June 16-17 (next week — pivotal meeting)",
        "fed_rate": "3.63%",
        "fed_commentary": "Fed blackout. Rate hike by year-end widely expected after hot CPI and NFP.",
        "fed_prob": "~78% year-end hike",
        "earnings_week": [
            ("Fri", "SPCX", "SpaceX", "IPO debut", "$135 priced", "$75B raised", "+19% first day"),
        ],
        "key_levels": [
            ("S&P 500", "7,250", "7,500", "7,380", "SpaceX bounce lifted S&P; key test at 7,420 resistance"),
            ("Nasdaq", "25,000", "26,200", "25,709 est.", "SPCX added to Nasdaq — rebalancing pressure fading"),
            ("BTC", "98,000", "108,000", "103,000", "Risk appetite returning"),
            ("Gold", "3,230", "3,320", "3,265", "Gold softening as equity risk appetite improves"),
        ],
    },

    "2026-06-15": {
        "tone": "Bullish",
        "tldr": [
            "US-Iran peace deal announced: Trump signs MOU — Strait of Hormuz to reopen under 60-day framework",
            "S&P 500 surges 1.65% to 7,554; Nasdaq rockets 3.07% to 26,684; Dow +0.92% to 51,671",
            "SpaceX (SPCX) extends IPO gains, hitting all-time high of $225.64 Monday",
            "Oil prices fall sharply on Strait reopening news; energy sector retreats, tech surges",
        ],
        "fg": ("~45", "Fear"),
        "aaii": ("32", "38", "30"),
        "geopolitical": {
            "global": "US and Iran announce Memorandum of Understanding: 60-day ceasefire framework, Strait of Hormuz reopening, nuclear talks to begin.",
            "us": "Trump signs MOU — 'biggest diplomatic win of my second term.' Intel-Apple chip deal rumors emerge mid-day. SpaceX at ATH.",
            "energy": "WTI Crude drops 4-6% on Strait reopening news — largest one-day oil drop in months. Energy sector (XLE) falls 2%+.",
        },
        "market_summary": "The day investors had been waiting for arrived as President Trump announced a memorandum of understanding to end the US-Iran conflict. The news triggered the largest single-day advance in weeks, with the Nasdaq surging over 3% as the Iran risk premium collapsed, energy prices plunged, and AI semiconductor stocks roared back. SpaceX extended its IPO gains, touching an all-time high of $225.64. The rally was broad-based with every major sector participating except energy, which fell as oil prices dropped sharply on news the Strait of Hormuz would reopen. Inflation expectations fell alongside oil prices, reducing the near-term Fed hike probability.",
        "opportunities": [
            "Semiconductor recovery trade — Nvidia, AMD, Micron all severely oversold after last week's crash; Iran resolution removes key inflation headwind",
            "Airline, shipping, and consumer discretionary — Iran deal reduces energy cost pressure on margin",
            "Rate expectations may ease: oil-driven CPI could fall toward 3.5-3.7% if Strait normalizes, reducing Fed hike probability",
        ],
        "risks": [
            "FOMC Wednesday (June 17) could still deliver hawkish dot plot — inflation data from May is baked in regardless of Iran deal",
            "Iran MOU is preliminary (60-day framework) — permanent deal requires congressional approval and Iran parliamentary ratification",
            "SpaceX at ATH may be overextended — profit-taking after 67% gain from IPO price",
        ],
        "fomc": "June 16-17 — Warsh's first meeting as Fed Chair",
        "fed_rate": "3.63%",
        "fed_commentary": "Fed blackout continues. FOMC 2-day meeting begins Tuesday. Iran deal may reduce inflation pressure, but May CPI data is locked in for dot plot.",
        "fed_prob": "~60% year-end hike — slightly reduced from 78% on Iran deal/oil drop",
        "earnings_week": [
            ("No major", "earnings", "this week", "—", "—", "—", "FOMC week"),
        ],
        "key_levels": [
            ("S&P 500", "7,450", "7,650", "7,554", "Reclaimed 7,500; targeting 7,600 retest"),
            ("Nasdaq", "26,400", "27,200", "26,684", "SPCX ATH + Iran deal drives 3% surge; 27K in sight"),
            ("BTC", "102,000", "114,000", "108,000", "Risk-on crypto surge on Iran deal"),
            ("Gold", "3,150", "3,250", "3,180", "Gold softens as geopolitical risk premium reduces"),
        ],
    },

    "2026-06-16": {
        "tone": "Cautiously Bullish",
        "tldr": [
            "FOMC 2-day meeting begins; markets trade cautiously awaiting Wednesday's rate decision and dot plot",
            "Intel shares rise on disclosure of 18A-P node entering risk production at VLSI Symposium in Honolulu",
            "SpaceX (SPCX) reaches all-time high of $225.64 before settling as profit-taking emerges",
            "Tech sector leads; defensives lag as Iran deal optimism sustains risk-on sentiment",
        ],
        "fg": ("~44", "Fear"),
        "aaii": ("32", "38", "30"),
        "geopolitical": {
            "global": "Iran peace framework being reviewed by Iranian parliament. UN observers prepare for deployment to Strait of Hormuz.",
            "us": "Intel discloses at VLSI Symposium (Honolulu) that 18A-P node has entered risk production — the specific process variant for Apple chips.",
            "energy": "Oil stabilizes after Monday's drop. WTI Crude around $68-70/barrel. Market assessing true timeline for Strait normalization.",
        },
        "market_summary": "Markets held near their post-Iran-deal highs in a session dominated by anticipation of Wednesday's FOMC decision. Intel was the day's standout story, rallying on disclosure at the VLSI Symposium that its 18A-P chip manufacturing node had entered risk production — a critical step toward what would become the Apple chip deal announced two days later. SpaceX briefly touched its all-time high of $225.64 before settling. Technology led while defensives lagged in a classic risk-on rotation. Breadth was positive but narrower than Monday's explosive move as traders awaited clarity from the Fed.",
        "opportunities": [
            "Intel (INTC) — 18A-P node entering production is first tangible evidence foundry strategy is working; Apple deal rumors add upside",
            "Semiconductor recovery continuing — AMD, Nvidia, Marvell all recovering toward pre-crash levels",
            "Small-cap and cyclicals may re-rate if Fed dot plot is less hawkish than feared given Iran deal oil drop",
        ],
        "risks": [
            "Fed dot plot Wednesday — median showing hike by year-end would be market negative despite Iran deal relief",
            "Iran MOU not yet fully ratified; parliamentary opposition in Iran could unwind weekend deal",
            "SpaceX at $225 is 67% above IPO price in 4 trading days — crowded long positioning makes correction risk high",
        ],
        "fomc": "June 17 (tomorrow) — Warsh presser at 2:30 PM ET",
        "fed_rate": "3.63%",
        "fed_commentary": "Meeting in session. No public commentary. Markets watching for dot plot showing 3.75-4.00% median year-end rate.",
        "fed_prob": "~95% hold tomorrow; 60% year-end hike probability",
        "earnings_week": [
            ("No major", "earnings", "this week", "—", "—", "—", "FOMC focus"),
        ],
        "key_levels": [
            ("S&P 500", "7,480", "7,650", "7,520-7,560", "Holding above 7,500; FOMC could break either way"),
            ("Nasdaq", "26,300", "27,300", "26,400-26,700", "SPCX ATH + semiconductor recovery"),
            ("BTC", "104,000", "116,000", "110,000", "Crypto rallying with equities"),
            ("Gold", "3,140", "3,240", "3,170", "Gold declining as risk-on dominates"),
        ],
    },

    "2026-06-17": {
        "tone": "Bearish",
        "tldr": [
            "Fed holds rates at 3.50-3.75% but dot plot shocks markets: 9 of 18 members project a hike before year-end",
            "S&P 500 falls 1.21% to 7,420; Nasdaq drops 1.34% to 26,022; Dow −0.98% to 51,493",
            "Warsh's first presser: 'price stability is our North Star' — language more hawkish than market hoped",
            "Fed raises PCE inflation forecast to 3.6% (vs 2.7% March) and lowers GDP; unemployment raised to 4.3%",
        ],
        "fg": ("~37", "Fear"),
        "aaii": ("30", "40", "30"),
        "geopolitical": {
            "global": "US-Iran MOU formally signed today in Geneva by both presidents — landmark diplomatic achievement.",
            "us": "FOMC dominates: Warsh holds rates but dot plot hawkish surprise. Retail Sales for May strong (+0.7% MoM).",
            "energy": "Oil drops on Iran MOU signing but recovers as Fed hawkishness signals demand resilience.",
        },
        "market_summary": "Kevin Warsh's first FOMC meeting as Federal Reserve Chair delivered a split verdict for markets. As expected, the Fed held rates steady at 3.50-3.75%, but the dot plot revealed a hawkish shift: nine of eighteen members projected at least one rate hike by year-end, with the median year-end rate target rising to 3.8%. Warsh's press conference emphasized 'price stability' as the committee's 'North Star,' reinforced the shorter, cleaner statement format, and notably — in a procedural first — declined to place his own dot on the plot. Markets sold off sharply, reversing much of Monday and Tuesday's Iran deal gains. The US-Iran MOU signing in Geneva occurred simultaneously, creating an unusual dual narrative of diplomatic progress and monetary tightening.",
        "opportunities": [
            "Bond duration play: if next CPI print shows oil-driven inflation moderating, rate hike odds may fall and bonds rally",
            "Defensive dividend growers (XLU, XLP) as investors de-risk growth exposure under rate hike scenario",
            "Currency (USD strength): DXY likely moves higher on Fed hawkishness — USD-long trade thesis strengthened",
        ],
        "risks": [
            "Multiple compression in growth stocks: every 25bp hike reduces Nasdaq valuation by ~5-8% mechanically",
            "Dot plot debate not over — Warsh's 'no dot' decision unusual; markets may fear uncertainty at next meeting",
            "Iran MOU is 60-day framework — completion depends on nuclear talks succeeding; oil market impact may reverse",
        ],
        "fomc": "June 17 — FOMC DECISION. Rates held 3.50-3.75%. Dot plot hawkish: median year-end rate 3.8%. Warsh: 'Price stability is our North Star.'",
        "fed_rate": "3.63% (range: 3.50-3.75% unchanged)",
        "fed_commentary": "Warsh: no dot provided (procedural first). Shorter statement removing outdated language. PCE forecast raised to 3.6%. GDP lowered. Unemployment raised to 4.3%.",
        "fed_prob": "9/18 FOMC members project year-end hike. CME FedWatch: ~65% hike probability by November 2026.",
        "earnings_week": [
            ("No major", "earnings", "today", "—", "—", "—", ""),
            ("Today", "—", "Retail Sales May 2026", "8:30 AM data: +0.7% MoM", "—", "—", "Beat"),
        ],
        "key_levels": [
            ("S&P 500", "7,350", "7,550", "7,420", "Post-FOMC selloff; 7,350 is critical support"),
            ("Nasdaq", "25,700", "26,700", "26,022", "Rate hike fear = multiple compression; 25,700 critical"),
            ("BTC", "100,000", "112,000", "106,000", "Crypto sells off on rate hike fears"),
            ("Gold", "3,150", "3,260", "3,210", "Gold mixed: rate hike negative but dollar safe haven"),
        ],
    },

    "2026-06-18": {
        "tone": "Bullish",
        "tldr": [
            "S&P 500 rebounds +1.2% as markets recover from FOMC shock — Intel-Apple chip deal confirmed by Trump",
            "Intel surges 10.6% on Apple partnership to build chips in the US using Intel 18A-P node",
            "Russell 2000 hits record close as rate expectations moderate and small-cap rotation resumes",
            "Nasdaq outperforms on Intel-Apple news; Iran-US MOU signed yesterday backstops optimism",
        ],
        "fg": ("~42", "Fear"),
        "aaii": ("30", "40", "30"),
        "geopolitical": {
            "global": "Iran MOU signed in Geneva yesterday — ceasefire framework active; 60-day clock toward permanent deal begins.",
            "us": "Trump announces Apple will use Intel to design and build chips domestically. Intel 18A-P process for lower-end chips (TSMC retains flagship orders). Historic for US semiconductor manufacturing.",
            "energy": "Oil fell after MOU signing. WTI near $65-67/barrel. Strait of Hormuz mine-clearing operations reportedly beginning.",
        },
        "market_summary": "Markets staged an impressive recovery from Wednesday's FOMC shock as a new catalyst arrived: President Trump confirmed Apple had agreed to work with Intel to manufacture chips domestically using the 18A-P node. Intel surged 10.6%, extending what became a remarkable 240%+ year-to-date gain for the chipmaker. The announcement was viewed as a validation of Intel's foundry turnaround strategy and a win for US semiconductor manufacturing policy. The Russell 2000 hit a record close, suggesting the rate environment was manageable for small-cap companies. Markets headed into the Juneteenth long weekend on a constructive note, with two major uncertainties — FOMC and Iran — largely resolved.",
        "opportunities": [
            "Intel remains a multi-year foundry turnaround story — Apple deal validates the 18A node; further customer wins possible",
            "US semiconductor manufacturing renaissance — INTC, MCHP and domestic fab names benefit from reshoring policy",
            "Small-cap rally has room — Russell 2000 at record; if inflation continues to moderate, rate cuts re-enter picture in 2027",
        ],
        "risks": [
            "Intel-Apple deal scope limited: lower-end chips only; TSMC retains 90%+ of Apple orders. Stock reaction may be overdone.",
            "FOMC hawkishness from yesterday hasn't vanished — next week's PCE data will be closely watched",
            "Juneteenth weekend liquidity concerns — thin markets heading into holiday",
        ],
        "fomc": "Done — held at 3.50-3.75%. Next FOMC: late July 2026.",
        "fed_rate": "3.63% (range 3.50-3.75%)",
        "fed_commentary": "No Fed speakers — post-meeting blackout period now lifted but no scheduled appearances. Markets watch next data prints (PCE June 25, NFP July 2).",
        "fed_prob": "~65% year-end hike probability. Next meeting: late July 2026.",
        "earnings_week": [
            ("No major", "earnings", "today", "—", "—", "—", ""),
        ],
        "key_levels": [
            ("S&P 500", "7,400", "7,600", "7,509 est.", "Recovering; 7,550 next resistance"),
            ("Nasdaq", "25,900", "26,800", "26,300 est.", "Intel-Apple halo lifts Nasdaq; 26,800 near-term target"),
            ("BTC", "102,000", "114,000", "108,000", "Risk-on recovery with equities"),
            ("Gold", "3,130", "3,220", "3,165", "Gold softens as risk appetite improves"),
        ],
    },

    "2026-06-22": {
        "tone": "Bearish",
        "tldr": [
            "S&P 500 slides 0.37% to 7,473; Nasdaq falls 1.32% to 26,167 as post-Iran-deal euphoria fades",
            "Technology stocks face renewed pressure as SpaceX drops below IPO debut price amid $600B sector selloff",
            "Markets bracing for PCE inflation data (June 25) and Micron earnings (June 24 after close)",
            "DXY holds near 120 as Fed rate hike expectations keep dollar elevated",
        ],
        "fg": ("~30", "Fear"),
        "aaii": ("34", "37", "29"),
        "geopolitical": {
            "global": "US-Iran MOU implementation underway; Iranian parliament ratification vote pending. Strait of Hormuz mine-clearing operations progressing.",
            "us": "Iran deal implementation concerns emerge — Iranian hardliners opposing nuclear provision of framework. Market reprices geopolitical risk slightly.",
            "energy": "Oil edges higher on uncertainty about Iran framework durability. WTI near $68. SpaceX below IPO debut price as reset from $225 ATH continues.",
        },
        "market_summary": "The post-FOMC and post-Iran-deal rally ran out of momentum on Monday as markets returned to pricing macro headwinds. Technology stocks led the decline, with SpaceX notably falling below its June 12 IPO debut price of $161 as the $400+ billion market cap tech selloff hit even newly minted public companies. The FOMC's hawkish dot plot continued to weigh on growth stock valuations, and investors looked ahead to a data-heavy week — Micron earnings and PCE inflation — for direction. The dollar remained near multi-year highs as DXY held 120, a significant headwind for earnings from multinational companies.",
        "opportunities": [
            "Micron earnings Wednesday after close — setup compelling: stock near 52-week highs, AI memory demand accelerating, estimates may prove conservative",
            "FedEx Q4 earnings Tuesday — logistics bellwether; better margins signal freight recovery post-Hormuz",
            "PCE data Thursday: if core PCE comes in at/below 3.4%, rate hike probability could soften and provide equity relief",
        ],
        "risks": [
            "SpaceX sub-$161 is technically bearish — IPO momentum broken; Nasdaq-100 rebalancing sellers still active",
            "Iran hardliner opposition to nuclear framework — deal could unravel, sending oil back above $80+",
            "Dollar at 120 creates earnings headwind for major multinationals (AAPL, MSFT, GOOGL) — margin compression risk",
        ],
        "fomc": "Done — July meeting is next. Markets watching PCE for rate hike confirmation.",
        "fed_rate": "3.63%",
        "fed_commentary": "Post-FOMC: several Fed speakers beginning to appear. Hawkish lean consistent with dot plot.",
        "fed_prob": "~65% year-end hike probability",
        "earnings_week": [
            ("Tue", "FDX", "FedEx", "After", "$5.92", "$24.0B", "±4%"),
            ("Wed", "MU", "Micron Technology", "After", "$20.20", "$35.69B", "±8%"),
            ("Fri", "NKE", "Nike Q4 announcement", "Fri 6/26", "—", "—", "(Actual results June 30)"),
        ],
        "key_levels": [
            ("S&P 500", "7,350", "7,550", "7,473", "Holding above 7,350; break risks June low retest"),
            ("Nasdaq", "25,500", "26,700", "26,167", "SPCX below IPO price; semi strength needed"),
            ("BTC", "100,000", "110,000", "105,000", "Volatile; watching 100K floor"),
            ("Gold", "3,160", "3,260", "3,210", "Gold steady on geopolitical uncertainty"),
        ],
    },

    "2026-06-23": {
        "tone": "Bearish",
        "tldr": [
            "Tech and semiconductor stocks continue their losing streak; Nasdaq marks third consecutive down day",
            "FedEx Q4 FY2026 beats estimates: EPS $6.41 vs $5.92 expected; revenue $25.0B vs $24.0B — stock rallies",
            "SpaceX shares rebound from below-IPO lows as $89B bond demand signal attracts buyers",
            "Markets digesting Conference Board Consumer Confidence data and awaiting Micron earnings tomorrow",
        ],
        "fg": ("~29", "Fear"),
        "aaii": ("34", "37", "29"),
        "geopolitical": {
            "global": "US-Iran: Iranian parliament formally voted to endorse MOU framework. Implementation clock officially begins. Strait of Hormuz mine-clearing 35% complete.",
            "us": "FedEx beat signals resilient freight demand post-Hormuz. Consumer confidence data moderates on energy prices.",
            "energy": "Oil slips slightly on Iranian parliamentary confirmation of deal durability. WTI near $67.",
        },
        "market_summary": "Technology stocks extended their losing streak as broader sector de-risking continued ahead of Micron's critical earnings report Wednesday after the bell. The day's brightest spot was FedEx, which surged after delivering a strong Q4 beat — EPS of $6.41 against $5.92 expectations — in a report that also reflected the final full quarter post-FedEx Freight spin-off. SpaceX bonds drew an extraordinary $89 billion in demand for an offering, signaling institutional confidence in the company despite equity volatility. Markets remained cautious, with investors managing position sizing ahead of Micron and Thursday's PCE data, the last major data release before the July FOMC meeting.",
        "opportunities": [
            "FedEx confirms economic resilience — logistics demand healthy post-Hormuz; XLI industrials may benefit from same",
            "SpaceX bond demand ($89B for $4.5B offering) signals institutional interest remains strong despite stock volatility",
            "Micron asymmetric setup: AI memory demand unprecedented; if Q3 beats, MU could be the catalyst to break tech sector out of losing streak",
        ],
        "risks": [
            "Nasdaq consecutive down days signal momentum reversal risk — fourth consecutive loss possible if Micron disappoints",
            "Consumer confidence declining: Conference Board reading showed future expectations falling — consumer spending risk",
            "Dollar DXY at 120 remains headwind for S&P 500 multinational earnings in Q2 reports coming in July",
        ],
        "fomc": "July meeting — key. PCE data Thursday will refine hike probability.",
        "fed_rate": "3.63%",
        "fed_commentary": "Fed speakers emerging post-blackout with hawkish lean. 'Data dependent' language prevails.",
        "fed_prob": "~65% year-end hike probability",
        "earnings_week": [
            ("Tue", "FDX", "FedEx Q4 FY26", "After", "$5.92 est → $6.41 actual", "$24.0B est → $25.0B actual", "Beat — stock rallies"),
            ("Wed", "MU", "Micron Technology Q3 FY26", "After", "$20.20", "$35.69B", "Pending — huge expectations"),
        ],
        "key_levels": [
            ("S&P 500", "7,300", "7,500", "7,380-7,420", "Tech weakness pushing S&P lower; 7,300 key floor"),
            ("Nasdaq", "25,200", "26,300", "25,500-25,800", "Third consecutive decline; oversold but no catalyst yet"),
            ("BTC", "99,000", "108,000", "103,500", "Crypto weak with equities"),
            ("Gold", "3,170", "3,270", "3,220", "Gold stable; PCE data tomorrow key"),
        ],
    },

    "2026-06-24": {
        "tone": "Cautious",
        "tldr": [
            "S&P 500 falls 0.10% to 7,358; Nasdaq drops 0.43% to 25,477 as markets await Micron earnings after close",
            "Micron (MU) Q3 FY2026 after close: BLOWOUT — EPS $25.11 vs $20.20 est; revenue $41.5B vs $35.69B est; GM 84.9%",
            "SpaceX bond draws $89B demand, but equity continues consolidation phase",
            "Markets tentatively stable early in session before late-day tech weakness drags indices lower",
        ],
        "fg": ("28", "Fear"),
        "aaii": ("34", "37", "29"),
        "geopolitical": {
            "global": "Iran MOU implementation proceeding. Hormuz passage reopening for commercial traffic expected within weeks. Oil markets stable.",
            "us": "Final GDP Q1 2026 revision released. Consumer spending data mixed ahead of tomorrow's PCE print.",
            "energy": "Oil steady near $66-68. Natural gas declining as Hormuz reopening timeline clarifies.",
        },
        "market_summary": "A muted, uncertain session as markets traded sideways awaiting what would prove to be one of the most spectacular earnings reports in semiconductor history. The S&P 500 and Nasdaq both declined modestly during regular trading, with investors unwilling to commit directionally ahead of Micron's after-hours report. After the bell, Micron shattered expectations: fiscal Q3 revenue of $41.5 billion — a company record — obliterated the $35.69 billion consensus by $5.8 billion. EPS of $25.11 crushed the $20.20 estimate. Gross margins reached a record 84.9%. The company announced $100 billion in minimum contracted revenue across 16 multi-year supply agreements. MU surged 13-17% in after-hours trading.",
        "opportunities": [
            "Micron (MU) after-hours surge: AI memory demand entered a new phase; HBM4 demand from hyperscalers unprecedented — buy MU on the open",
            "Semiconductor sector recovery catalyst: Micron's beat could be the capitulation point for the post-June 5 selloff",
            "PCE data tomorrow: if core PCE meets/beats expectations (3.4% YoY), dual catalyst of Micron + PCE could spark sharp rally",
        ],
        "risks": [
            "Micron after-hours surge may fade at open as 'sell the news' pattern emerges (happened in prior cycles)",
            "Even with Micron beat, broader Nasdaq has been falling 4 days — structural selling may overwhelm the catalyst",
            "PCE tomorrow: any upside surprise (+3.6%+ core) could negate Micron enthusiasm",
        ],
        "fomc": "July meeting upcoming. PCE tomorrow critical.",
        "fed_rate": "3.63%",
        "fed_commentary": "Hawkish Fed commentary continuing post-FOMC. PCE data tomorrow is the next key input.",
        "fed_prob": "~65% year-end hike",
        "earnings_week": [
            ("Tue", "FDX", "FedEx Q4 FY26", "After", "Beat", "$25.0B vs $24.0B est", "Strong"),
            ("Wed after", "MU", "Micron Q3 FY26", "After", "$25.11 vs $20.20 est", "$41.5B vs $35.69B est", "BLOWOUT +17% AH"),
        ],
        "key_levels": [
            ("S&P 500", "7,300", "7,500", "7,358", "Approaching June lows; Micron catalyst needed"),
            ("Nasdaq", "25,000", "26,000", "25,477", "4th consecutive decline — Micron beat critical catalyst"),
            ("BTC", "98,000", "107,000", "102,000", "Holding near 100K"),
            ("Gold", "3,180", "3,280", "3,235", "Safe haven bid building ahead of PCE"),
        ],
    },

    "2026-06-25": {
        "tone": "Cautious",
        "tldr": [
            "Micron +17% at open after blowout Q3 (EPS $25.11 vs $20.20 est; rev $41.5B vs $35.69B) but Nasdaq still falls 0.46%",
            "PCE May 2026: +0.4% MoM, +4.1% YoY (in line); Core PCE +0.3% MoM, +3.4% YoY — Fed holds",
            "Nasdaq logs 4th consecutive decline — first such streak since February 2026",
            "Dow edges up 0.14% to 51,921 as rotation favors industrials; S&P flat at 7,357",
        ],
        "fg": ("~27", "Fear"),
        "aaii": ("34", "37", "29"),
        "geopolitical": {
            "global": "Iran MOU implementation on track. Hormuz commercial traffic increasing daily. OPEC+ monitoring supply dynamics as Iranian oil re-enters market.",
            "us": "PCE data in-line with expectations — neither hawkish nor dovish surprise. Fed on hold through summer likely.",
            "energy": "Oil falls on in-line PCE and Hormuz reopening confirmation. WTI near $64-66.",
        },
        "market_summary": "Despite Micron's extraordinary 17% open-market surge following its record-breaking Q3 earnings, the Nasdaq logged its fourth consecutive daily decline — a streak not seen since February. Investors appeared to use Micron's strength as an opportunity to reduce other technology positions, evidencing a sector-wide repositioning rather than indiscriminate buying. The PCE inflation report for May came in benign and in-line: headline +4.1% YoY (vs 4.1% expected), core +3.4% YoY (matching estimates). This 'not worse than feared' print failed to reignite meaningful buying. The Dow's slight gain, led by industrials and healthcare, reflected ongoing rotation dynamics. The week ended with markets uncertain about direction heading into summer.",
        "opportunities": [
            "Micron's $100B contracted revenue announcement represents multi-year AI memory demand visibility — dip buyers may target MU pullbacks",
            "In-line PCE suggests Fed will pause and assess — bond market rally possible as hike fears moderate",
            "Dow and cyclicals: if inflation continuing to normalize, early-cycle rotation back to value could persist",
        ],
        "risks": [
            "Nasdaq 4-day losing streak breaking technical structure — if 25,000 doesn't hold, June lows at 25,170 then 24,500 in view",
            "Micron surge masking broad tech weakness: selling pressure in AAPL, MSFT, GOOGL, META suggests broad deleveraging",
            "PCE at 4.1% is still well above Fed target — 'in-line' doesn't mean resolved; summer data could reignite hike fears",
        ],
        "fomc": "July meeting upcoming. In-line PCE supports 'hold' scenario for July; year-end hike still probable.",
        "fed_rate": "3.63%",
        "fed_commentary": "PCE in-line; Fed speakers note 'progress is being made but more is needed.' July hold widely expected.",
        "fed_prob": "~60% year-end hike probability. July hold: ~90% probability.",
        "earnings_week": [
            ("Tue", "FDX", "FedEx Q4 FY26", "After", "Beat $6.41 EPS", "$25.0B rev", "Strong"),
            ("Wed AH", "MU", "Micron Q3 FY26", "After", "$25.11 EPS", "$41.5B rev", "BLOWOUT — MU +17%"),
        ],
        "key_levels": [
            ("S&P 500", "7,280", "7,450", "7,357", "4-week closing low; 7,280 is critical; hold or accelerate lower"),
            ("Nasdaq", "24,800", "25,800", "25,359", "4th consecutive loss; 24,800 major support"),
            ("BTC", "97,000", "107,000", "101,500", "Crypto near 100K support; watching for breakdown or bounce"),
            ("Gold", "3,190", "3,290", "3,245", "Gold strengthening on in-line PCE; rate hike fears moderating"),
        ],
    },
}

# ---------------------------------------------------------------------------
# Weekly summaries
# ---------------------------------------------------------------------------

WEEKLY = {
    "2026-06-01": {  # week of June 1-5
        "sector_narrative": "Technology (XLK) was the week's worst performer after starting as the best — Broadcom's guidance disappointment and the hot NFP print triggered a sector-wide reversal. Energy (XLE) outperformed on elevated oil prices from ongoing Strait of Hormuz disruption. Consumer Staples (XLP) and Utilities (XLU) held up as defensives attracted rotation capital after Thursday-Friday's growth selloff.",
        "vol_interpretation": "VIX spiked sharply as the week progressed, rising from ~16 Monday to 22+ by Friday after NFP. VIX9D exceeded VIX briefly on Friday — rare backwardation signal indicating acute near-term fear. Options markets saw heavy put buying in semiconductor names.",
        "top_gainers": [
            ("1", "MRVL", "Marvell Technology", "Semiconductors", "+12% Mon-Tue (Jensen Huang catalyst)", "Nvidia CEO calls it next trillion-dollar company"),
            ("2", "SMCI", "Super Micro Computer", "AI Infrastructure", "+8%", "AI server buildout demand"),
            ("3", "HPE", "Hewlett Packard Enterprise", "Tech Hardware", "+6%", "Q2 beat; AI enterprise demand"),
            ("4", "XOM", "Exxon Mobil", "Energy", "+5%", "Oil prices elevated; Strait disruption premium"),
            ("5", "CVX", "Chevron", "Energy", "+4%", "Energy sector outperform on oil strength"),
        ],
        "top_losers": [
            ("1", "MRVL", "Marvell Technology", "Semiconductors", "−16% by Fri (−16% on Fri alone)", "NFP + AVGO guidance miss contagion"),
            ("2", "MU", "Micron Technology", "Semiconductors", "−13%", "Semiconductor sector selloff"),
            ("3", "AMD", "Advanced Micro Devices", "Semiconductors", "−11%", "AI cycle peak fears"),
            ("4", "INTC", "Intel", "Semiconductors", "−11%", "Broad chip selloff"),
            ("5", "AVGO", "Broadcom", "Semiconductors", "−20%+ on week", "No guidance raise disappoints"),
        ],
        "market_moving_release": "May NFP (June 5): +172K jobs vs ~80K expected. Unemployment 4.3%. Hotter-than-expected print triggered rate hike repricing and the primary catalyst for Friday's 4%+ Nasdaq crash.",
        "data_trend_summary": "Labor market remains exceptionally resilient — NFP double consensus, wage growth solid. ADP earlier in week also strong. ISM Services solid. Inflation data (CPI/PPI) next week will be critical.",
        "fed_speakers": "Fed blackout from Friday June 6 ahead of FOMC.",
        "fed_key_quotes": "'Data will guide the committee' — pre-blackout language from officials.",
        "geopolitical_weekly": "US-Iran ceasefire (April 7-8) holding through week. Strait of Hormuz commercial traffic still severely disrupted. Oil prices remain elevated, feeding into energy-driven CPI acceleration expected in next week's report.",
        "next_week_calendar": [
            ("Mon", "No major data", "", ""),
            ("Tue", "No major data", "", ""),
            ("Wed", "CPI May 2026", "4.0-4.2% expected YoY", "HIGH — Fed hike pivot risk"),
            ("Thu", "PPI May 2026", "6.0% YoY prior", "HIGH"),
            ("Fri", "SpaceX (SPCX) IPO Nasdaq debut", "$135/share, $75B raised", "HISTORIC"),
        ],
        "next_earnings": "SpaceX Nasdaq debut June 12. Quiet week for traditional earnings.",
        "next_fed_speakers": "FOMC blackout continues through June 17 meeting.",
        "market_summary": "A tale of two halves defined the week of June 1-5. Monday and Tuesday saw the S&P 500 make history — breaking above 7,600 for the first time — powered by Nvidia's new chip launch, Marvell's extraordinary 32% single-day gain, and US-Iran peace optimism. Then everything reversed. Broadcom's failure to raise AI guidance triggered a semiconductor crisis Wednesday-Thursday, followed by a catastrophic hot NFP print Friday that sent the Nasdaq down 4.18% — its worst day since April 2025. The week ended with the S&P down over 2% and the Nasdaq down 4.7%, wiping $1.3 trillion in semiconductor market cap and resetting the rate hike probability to 55%+.",
        "opportunities": [
            "Contrarian semiconductor recovery trade — AMD, Intel, Micron at multi-week lows with fundamental AI demand intact",
            "SpaceX IPO (June 12) — first-day pop thesis with $75B raise and massive institutional demand",
            "CPI Wednesday as binary event — if in-line or below 4.2%, rate fears ease and equities can recover",
        ],
        "risks": [
            "Rate hike by year-end now majority market view — growth stocks face structural multiple compression",
            "AI capex cycle peak narrative gaining traction — if Broadcom's cautiousness reflected real demand slowdown, semis have more to fall",
            "Iran ceasefire fragility — 60-day framework not yet formalized into permanent deal",
        ],
    },

    "2026-06-08": {  # week of June 8-12
        "sector_narrative": "Technology (XLK) rebounded Friday on SpaceX IPO euphoria after mid-week CPI-driven decline. Energy (XLE) fell sharply on CPI concerns about demand destruction. Financials (XLF) outperformed as rate hike expectations rose — banks benefit from steeper yield curve. Healthcare (XLV) and Consumer Staples (XLP) held up as defensives during Tuesday-Wednesday volatility.",
        "vol_interpretation": "VIX remained elevated (22-28 range) through most of the week. VIX spiked to near 28 on Wednesday (CPI day) before retreating as SpaceX IPO sentiment improved. Week ended with VIX ~24, reflecting ongoing uncertainty ahead of FOMC.",
        "top_gainers": [
            ("1", "SPCX", "SpaceX", "Aerospace/Technology", "+19% first day", "Largest IPO in history; world's largest IPO debut"),
            ("2", "XOM", "Exxon Mobil", "Energy", "+4%", "Elevated CPI confirms energy pricing power"),
            ("3", "JPM", "JPMorgan Chase", "Financials", "+3%", "Rate hike expectations boost bank earnings outlook"),
            ("4", "BAC", "Bank of America", "Financials", "+3%", "Steeper yield curve benefits NIM"),
            ("5", "GS", "Goldman Sachs", "Financials", "+2.5%", "Fixed income trading benefits from vol"),
        ],
        "top_losers": [
            ("1", "AMD", "Advanced Micro Devices", "Semiconductors", "−8%", "Semiconductor overhang continues; CPI concerns"),
            ("2", "NVDA", "Nvidia", "Semiconductors", "−5%", "Rate hike fears weigh on high-multiple growth"),
            ("3", "TSLA", "Tesla", "Consumer Discretionary", "−7%", "Rate sensitivity + EV demand concerns"),
            ("4", "META", "Meta Platforms", "Communication Services", "−4%", "Multiple compression as rates rise"),
            ("5", "NFLX", "Netflix", "Communication Services", "−3%", "Growth at risk from higher rates"),
        ],
        "market_moving_release": "CPI May 2026 (June 10): +4.2% YoY, +0.5% MoM — 3-year high. Dow fell 953 points. Energy component drove 60%+ of monthly increase. Cemented Fed hike path.",
        "data_trend_summary": "Inflation acceleration confirmed: CPI +4.2% and PPI +6.0% YoY signal pipeline inflation persists. Energy-driven price increases from Strait of Hormuz disruption now fully embedded in data. Rate hike by year-end near-certain heading into FOMC.",
        "fed_speakers": "Fed in blackout period. No public commentary.",
        "fed_key_quotes": "Futures markets: 78% year-end hike probability post-CPI.",
        "geopolitical_weekly": "US signals potential additional strikes in Iran (June 10) alarmed markets briefly before clarification. Peace framework talks continued. Strait of Hormuz mine-clearing progressing but weeks from full reopening. SpaceX debut symbol of US tech innovation amid geopolitical backdrop.",
        "next_week_calendar": [
            ("Mon", "Iran peace announcement", "MOU signing in Geneva expected", "MARKET MOVING"),
            ("Tue-Wed", "FOMC meeting", "June 16-17", "HIGH — Warsh first meeting"),
            ("Wed", "FOMC decision 2 PM ET", "Hold expected; dot plot key", "HIGH"),
            ("Thu", "Retail Sales May", "8:30 AM", "Medium"),
        ],
        "next_earnings": "No major earnings this week. FOMC is the focus.",
        "next_fed_speakers": "FOMC June 16-17. Warsh press conference June 17 at 2:30 PM ET.",
        "market_summary": "Week 2 was defined by two anchoring events: the most painful inflation print in three years (CPI +4.2%) on Wednesday and the most euphoric market event of the year (SpaceX's historic IPO) on Friday. Between them, markets whipsawed — the Dow broke below 50,000 for the first time since before the Iran conflict rally, then recovered on SpaceX enthusiasm. CPI confirmed the Fed's hand is being forced: energy-driven inflation from the Strait of Hormuz closure is filtering through the entire price chain. The week ended with risk sentiment improved from Wednesday's lows but the macro picture firmly hawkish heading into the FOMC meeting.",
        "opportunities": [
            "SpaceX (SPCX) momentum — stock hit ATH of $225.64 the following Monday; strong institutional support validated",
            "Financial sector — rate hike environment directly benefits bank net interest margins; XLF outperforming",
            "Iran deal next week — MOU expected to be signed, potentially removing the key inflation driver",
        ],
        "risks": [
            "FOMC dot plot could show multiple hikes — Warsh's first meeting sets the tone for years",
            "CPI structural issue: energy inflation leads to second-round effects in services and wages",
            "SpaceX rebalancing mechanics force ongoing selling in tech peers — Nasdaq cap structure under pressure",
        ],
    },

    "2026-06-15": {  # week of June 15-18 (Juneteenth = closed Friday)
        "sector_narrative": "Technology (XLK) dominated with Intel (+10.6%) and SpaceX enthusiasm powering Monday's 3%+ Nasdaq gain. Energy (XLE) declined as Iran deal sent oil prices sharply lower. Small-cap (Russell 2000) hit a record close Thursday — outperforming large-cap as rate expectations moderated post-deal. Utilities and defensives lagged as risk appetite returned early week before fading Wednesday on FOMC hawkishness.",
        "vol_interpretation": "VIX collapsed from ~24 Monday open to ~18 by Thursday. The Iran deal and Intel-Apple news were natural volatility suppressors. FOMC Wednesday briefly spiked VIX to ~22 before Thursday recovery. Week ended with VIX ~19 — improved but not complacent.",
        "top_gainers": [
            ("1", "INTC", "Intel", "Semiconductors", "+16%+ on week (+10.6% Thu alone)", "Apple chip manufacturing deal — foundry validation"),
            ("2", "SPCX", "SpaceX", "Aerospace/Technology", "+ATH $225.64 Mon", "Post-IPO momentum; Iran deal tailwind"),
            ("3", "UAL", "United Airlines", "Airlines", "+8%", "Strait reopening = jet fuel cost reduction"),
            ("4", "DAL", "Delta Air Lines", "Airlines", "+7%", "Energy cost normalization beneficiary"),
            ("5", "IWM", "Russell 2000 ETF", "Small Cap", "+4%+ on week", "Record close; rate relief trade"),
        ],
        "top_losers": [
            ("1", "XOM", "Exxon Mobil", "Energy", "−6%", "Oil drops 4-6% on Iran deal"),
            ("2", "CVX", "Chevron", "Energy", "−5%", "Strait reopening reduces upstream premium"),
            ("3", "COP", "ConocoPhillips", "Energy", "−5%", "E&P sector hit by oil price decline"),
            ("4", "LNG", "Cheniere Energy", "Energy", "−4%", "LNG supply normalization expected"),
            ("5", "HAL", "Halliburton", "Energy Services", "−4%", "Rig count may decline as oil normalizes"),
        ],
        "market_moving_release": "FOMC decision (June 17): Rates held 3.50-3.75%. Dot plot showed 9/18 members projecting year-end hike. PCE forecast raised to 3.6%. Warsh press conference hawkish: 'price stability is our North Star.'",
        "data_trend_summary": "Retail Sales May +0.7% MoM (strong). FOMC dot plot marks hawkish pivot — median year-end rate target rose from 3.4% to 3.8%. US-Iran MOU signed June 17 in Geneva — oil price normalization expected over 60-day framework.",
        "fed_speakers": "Kevin Warsh (June 17 presser): declined to add dot; shorter statement; 'price stability is North Star'; first hike by year-end possible.",
        "fed_key_quotes": "'Price stability remains the committee's North Star.' — Warsh, June 17 presser",
        "geopolitical_weekly": "Transformative geopolitical week: US-Iran MOU announced Sunday June 14 by Trump, signed in Geneva June 17. Strait of Hormuz reopening begins. Iran parliament ratification pending. Intel-Apple domestic chip deal signals US manufacturing reshoring.",
        "next_week_calendar": [
            ("Mon", "No major data", "", ""),
            ("Tue", "Conference Board Consumer Confidence", "June reading", "Medium"),
            ("Thu", "PCE May 2026", "+4.1% YoY expected", "HIGH — Fed hike barometer"),
            ("Wed-Thu", "Micron Technology Q3 earnings", "After Wed close", "HIGH — $20B EPS estimate"),
        ],
        "next_earnings": "FedEx Q4 (Tue), Micron Q3 FY26 (Wed after close — consensus $20.20 EPS, +276% YoY rev).",
        "next_fed_speakers": "Post-FOMC Fed speakers expected Tuesday-Thursday.",
        "market_summary": "A historically significant week delivered two major catalysts in opposite directions. Monday's Iran peace deal sent the Nasdaq surging 3%, lifting hopes that the energy-driven inflation shock would soon moderate. Wednesday's FOMC hawkish surprise reversed much of that — the dot plot's shift toward rate hikes hit growth stocks hard. Thursday's Intel-Apple chip manufacturing deal restored optimism, and Russell 2000 hit a record close in a sign that smaller companies were benefiting from reduced energy costs. The 4-day holiday-shortened week ended on a constructive note: DXY near 120 but declining, oil falling, and Intel validated as a foundry competitor.",
        "opportunities": [
            "Intel foundry thesis fully validated — Apple deal signals more customers could follow; INTC up 240%+ YTD",
            "Airline, transportation, consumer discretionary — Strait reopening reduces key cost inputs; margins expand",
            "Rate expectations moderating: oil-driven inflation may peak; if next CPI print shows deceleration, hike probability falls",
        ],
        "risks": [
            "Dot plot is baked in — Warsh signaled hike bias; regardless of Iran deal, May data shows inflation at 4.2%",
            "Iran MOU is 60-day preliminary framework; nuclear talks could fail and reignite conflict",
            "SpaceX at $225 ATH — 67% above IPO price in 4 days is bubble territory; profit-taking will be severe",
        ],
    },

    "2026-06-22": {  # week of June 22-25 (partial — 4 days only, through our data)
        "sector_narrative": "Technology (XLK) underperformed for the fourth consecutive week, weighed down by SpaceX falling below IPO price and broad de-risking. Micron's extraordinary Thursday after-hours beat (+17% open Friday) was the week's standout but failed to lift the broad sector. Healthcare (XLV) and Industrials (XLI) led on FedEx beat and rate moderation. Energy (XLE) declined further as oil fell on Hormuz reopening progress.",
        "vol_interpretation": "VIX elevated at 18-20 range through the week. Micron earnings reduced fear Friday morning (VIX ~18.89 at Thursday close) but the fourth consecutive Nasdaq down day prevented a full recovery. Options markets showing elevated put activity in Nasdaq-100 components.",
        "top_gainers": [
            ("1", "MU", "Micron Technology", "Semiconductors", "+17% open Fri", "BLOWOUT Q3: EPS $25.11 vs $20.20; rev $41.5B vs $35.69B; 84.9% GM"),
            ("2", "FDX", "FedEx", "Industrials/Transportation", "+4-6%", "Q4 FY26 beat: EPS $6.41 vs $5.92; rev $25B vs $24B"),
            ("3", "UNH", "UnitedHealth Group", "Healthcare", "+3%", "Defensive rotation; healthcare holding up"),
            ("4", "JNJ", "Johnson & Johnson", "Healthcare", "+2.5%", "Safe-haven rotation"),
            ("5", "BA", "Boeing", "Industrials", "+2%", "Iran deal reduces fuel costs for airlines — positive for orders"),
        ],
        "top_losers": [
            ("1", "SPCX", "SpaceX", "Technology/Aerospace", "−$400B week; below IPO price", "Post-ATH profit-taking; rebalancing selling"),
            ("2", "NVDA", "Nvidia", "Semiconductors", "−5%", "Broad tech deleveraging despite AI demand intact"),
            ("3", "META", "Meta Platforms", "Communication Services", "−4%", "Multiple compression; DXY headwind"),
            ("4", "GOOGL", "Alphabet", "Communication Services", "−3%", "Ad revenue concerns as growth slows"),
            ("5", "TSLA", "Tesla", "Consumer Discretionary", "−5%", "Rate sensitivity; demand concerns"),
        ],
        "market_moving_release": "PCE May 2026 (June 25): Headline +0.4% MoM, +4.1% YoY; Core +0.3% MoM, +3.4% YoY — in line with expectations. Neither hawkish nor dovish; Fed hold in July confirmed.",
        "data_trend_summary": "Inflation decelerating: PCE came in line, core PCE stable at 3.4%. Combined with Iran deal and oil decline, the data flow suggests the worst of the energy-driven inflation may be past. However, 4.1% headline remains well above 2% target — multiple hikes may still be needed.",
        "fed_speakers": "Post-FOMC hawks emerged: Barkin, Kugler commented on needing further progress before cuts. 'Data dependent' mantra.",
        "fed_key_quotes": "'We have made progress but we need to see more.' — post-FOMC Fed official commentary",
        "geopolitical_weekly": "Iran MOU implementation progressing: Iranian parliament ratified framework; Hormuz mine-clearing 35% complete by week's end. OPEC+ monitoring supply normalization. SpaceX bond ($89B demand on $4.5B offering) signals institutional confidence despite equity volatility.",
        "next_week_calendar": [
            ("Mon", "No major data", "", ""),
            ("Tue", "S&P/Case-Shiller Home Price Index", "", "Low"),
            ("Wed", "ADP Private Payrolls", "June", "Medium"),
            ("Thu", "Initial Jobless Claims", "", "Medium"),
            ("Thu", "ISM Manufacturing PMI", "June", "High"),
            ("Fri", "June NFP Jobs Report", "Released July 2 (holiday schedule)", "HIGH"),
        ],
        "next_earnings": "Nike Q4 FY2026 results — June 30. Q4 beat expected driven by tariff refund benefit.",
        "next_fed_speakers": "Several Fed speakers expected week of June 29. July FOMC meeting approaches.",
        "market_summary": "The final full week of the first half ended with technology stocks in retreat and fundamental divergence widening. Micron's historic Q3 earnings — $41.5 billion in revenue, 84.9% gross margins, $100 billion in contracted revenue — represented a stunning validation of the AI memory cycle but couldn't arrest the broader Nasdaq's 4-day losing streak. FedEx's strong Q4 beat confirmed economic resilience. PCE came in line on Thursday, removing the tail risk of an accelerated hike timeline. The week illustrated the tension gripping markets: AI fundamentals remain extraordinary, but macro headwinds (rates, DXY, valuations) are forcing institutional repositioning. Markets enter July with the S&P 500 near 4-week lows despite exceptional corporate earnings.",
        "opportunities": [
            "Micron's $100B contracted revenue signals AI memory is in a multi-year supercycle — scale and margin will compound",
            "In-line PCE reduces hike urgency; if oil continues declining on Hormuz reopening, inflation could fall rapidly toward 3.5% by Q3",
            "Rotation into cyclicals and value is logical: industrials, healthcare, and financials are performing well in this environment",
        ],
        "risks": [
            "Tech sector technical deterioration: 4 consecutive Nasdaq down days; 25,000 level is the critical near-term floor",
            "SpaceX below IPO price signals early investors locking profits — index rebalancing headwinds persist through July",
            "July FOMC: rate hike probability at 65%+ means higher-for-longer messaging could put another 5-8% downside risk on Nasdaq",
        ],
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load(path):
    return path.read_text()

def save(path, content):
    path.write_text(content)

def replace_section(content, marker, new_content):
    """Replace content between marker and next '---' separator."""
    # Find the marker
    idx = content.find(marker)
    if idx == -1:
        return content
    # Find the end of this section (next ---)
    end_idx = content.find("\n---", idx)
    if end_idx == -1:
        end_idx = len(content)
    content = content[:idx] + new_content + content[end_idx:]
    return content

def build_tone(tone, tldr):
    lines = [f"## Market Tone\n**Overall:** {tone}\n\n**TL;DR:**"]
    for bullet in tldr:
        lines.append(f"- {bullet}")
    lines.append("")
    return "\n".join(lines) + "\n"

def build_sentiment(fg_score, fg_label, bulls, bears, neutral, reading=""):
    fg_str = f"{fg_score} — {fg_label}"
    lines = [
        "## Sentiment Gauges\n",
        f"- **CNN Fear & Greed Index:** {fg_str}",
        f"- **AAII Sentiment (latest weekly):** Bulls {bulls}% | Bears {bears}% | Neutral {neutral}%",
        f"- **Reading:** {reading}\n",
    ]
    return "\n".join(lines)

def build_geopolitical(global_, us, energy, dxy, yield10):
    lines = [
        "## Geopolitical & Macro Developments\n",
        f"- **Global:** {global_}",
        f"- **US:** {us}",
        f"- **Energy Markets:** {energy}",
        f"- **Currency (DXY):** {dxy}",
        f"- **Bond Market (10Y Yield):** {yield10}\n",
    ]
    return "\n".join(lines)

def build_key_levels(levels):
    lines = [
        "## Morning Setup — Key Levels to Watch\n",
        "| Index / Asset | Support | Resistance | Key Level | Notes |",
        "|---------------|---------|------------|-----------|-------|",
    ]
    for row in levels:
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} |")
    lines.append("")
    return "\n".join(lines)

def build_earnings_calendar(earnings):
    lines = [
        "## Earnings Calendar — This Week\n",
        "| Day | Ticker | Company | Time | EPS Est | Rev Est | Implied Move |",
        "|-----|--------|---------|------|---------|---------|--------------|",
    ]
    for row in earnings:
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6]} |")
    lines.append("")
    return "\n".join(lines)

def build_fed_watch_open(fomc, fed_rate, commentary, prob):
    return f"""## Fed Watch

- **Next FOMC Meeting:** {fomc}
- **Current Fed Funds Rate:** {fed_rate}
- **Overnight Fed Commentary:** {commentary}
- **Rate Change Probability (CME FedWatch):** {prob}
"""

def build_fed_watch_close(fomc, fed_rate, commentary, prob, activity, speaker, quote):
    return f"""## Fed Watch

- **Today's Fed Activity:** {activity}
- **Current Fed Funds Rate:** {fed_rate}
- **Rate Change Probability (CME FedWatch):** {prob}
- **Next FOMC Meeting:** {fomc}
- **Notable Fed Speaker(s) Today:** {speaker}
- **Key Quote:** {quote}
"""

def build_market_summary(summary):
    return f"## 1. Market Summary\n\n{summary}\n"

def build_opportunities(opps):
    lines = ["## 2. Opportunities\n"]
    for opp in opps:
        lines.append(f"- {opp}")
    lines.append("")
    return "\n".join(lines)

def build_risks(risks):
    lines = ["## 3. Risks\n"]
    for risk in risks:
        lines.append(f"- {risk}")
    lines.append("")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Fill Open report
# ---------------------------------------------------------------------------

def fill_open(path, date_str):
    d = DAILY.get(date_str)
    if not d:
        print(f"  No data for {date_str} — skipping")
        return
    content = load(path)

    # Extract DXY and yield from existing content
    dxy_match = re.search(r"\*\*Currency \(DXY\):\*\* ([\d,\.]+)", content)
    yield_match = re.search(r"\*\*Bond Market \(10Y Yield\):\*\* ([\d\.]+%)", content)
    dxy_val = dxy_match.group(1) if dxy_match else ""
    yield_val = yield_match.group(1) if yield_match else ""

    # Market Tone
    tone_block = build_tone(d["tone"], d["tldr"])
    content = replace_section(content, "## Market Tone", tone_block)

    # Earnings Calendar
    earnings_block = build_earnings_calendar(d.get("earnings_week", []))
    content = replace_section(content, "## Earnings Calendar — This Week", earnings_block)

    # Fed Watch
    fed_block = build_fed_watch_open(d["fomc"], d["fed_rate"], d["fed_commentary"], d["fed_prob"])
    content = replace_section(content, "## Fed Watch", fed_block)

    # Geopolitical
    geo = d["geopolitical"]
    geo_block = build_geopolitical(geo["global"], geo["us"], geo["energy"], dxy_val, yield_val)
    content = replace_section(content, "## Geopolitical & Macro Developments", geo_block)

    # Key Levels
    kl_block = build_key_levels(d.get("key_levels", []))
    content = replace_section(content, "## Morning Setup — Key Levels to Watch", kl_block)

    # Sentiment
    fg_score, fg_label = d["fg"]
    bulls, bears, neutral = d["aaii"]
    aaii_reading = "Below historical average bullishness — investors cautious amid macro uncertainty"
    sent_block = build_sentiment(fg_score, fg_label, bulls, bears, neutral, aaii_reading)
    content = replace_section(content, "## Sentiment Gauges", sent_block)

    # Market Summary, Opportunities, Risks
    ms_block = build_market_summary(d["market_summary"])
    content = replace_section(content, "## 1. Market Summary", ms_block)
    opp_block = build_opportunities(d["opportunities"])
    content = replace_section(content, "## 2. Opportunities", opp_block)
    risk_block = build_risks(d["risks"])
    content = replace_section(content, "## 3. Risks", risk_block)

    save(path, content)
    print(f"  ✓ Open filled: {path.name}")

# ---------------------------------------------------------------------------
# Fill Close report
# ---------------------------------------------------------------------------

def fill_close(path, date_str):
    d = DAILY.get(date_str)
    if not d:
        print(f"  No data for {date_str} — skipping")
        return
    content = load(path)

    dxy_match = re.search(r"\*\*Currency \(DXY\):\*\* ([\d,\.]+)", content)
    yield_match = re.search(r"\*\*Bond Market \(10Y Yield\):\*\* ([\d\.]+%)", content)
    dxy_val = dxy_match.group(1) if dxy_match else ""
    yield_val = yield_match.group(1) if yield_match else ""

    # Market Tone
    tone_block = build_tone(d["tone"], d["tldr"])
    content = replace_section(content, "## Market Tone", tone_block)

    # Fed Watch (close version)
    fed_block = build_fed_watch_close(
        d["fomc"], d["fed_rate"],
        d.get("fed_commentary", ""),
        d["fed_prob"],
        d.get("fed_activity", "No FOMC today."),
        d.get("fed_speaker", "None scheduled"),
        d.get("fed_quote", "'Data will guide the committee.'"),
    )
    content = replace_section(content, "## Fed Watch", fed_block)

    # Sentiment
    fg_score, fg_label = d["fg"]
    bulls, bears, neutral = d["aaii"]
    aaii_reading = "Sentiment tracking below historical average bullishness — macro uncertainty prevailing"
    sent_block = build_sentiment(fg_score, fg_label, bulls, bears, neutral, aaii_reading)
    content = replace_section(content, "## Sentiment Gauges", sent_block)

    # Geopolitical
    geo = d["geopolitical"]
    geo_block = build_geopolitical(geo["global"], geo["us"], geo["energy"], dxy_val, yield_val)
    content = replace_section(content, "## Geopolitical & Macro Developments", geo_block)

    # Market Summary, Opportunities, Risks
    ms_block = build_market_summary(d["market_summary"])
    content = replace_section(content, "## 1. Market Summary", ms_block)
    opp_block = build_opportunities(d["opportunities"])
    content = replace_section(content, "## 2. Opportunities", opp_block)
    risk_block = build_risks(d["risks"])
    content = replace_section(content, "## 3. Risks", risk_block)

    save(path, content)
    print(f"  ✓ Close filled: {path.name}")

# ---------------------------------------------------------------------------
# Fill Weekly report
# ---------------------------------------------------------------------------

def fill_weekly(path, week_monday_str):
    w = WEEKLY.get(week_monday_str)
    if not w:
        print(f"  No weekly data for {week_monday_str} — skipping")
        return
    content = load(path)

    # Sector rotation narrative (already has placeholder text)
    content = content.replace(
        "**Sector rotation narrative:**",
        f"**Sector rotation narrative:** {w['sector_narrative']}"
    )

    # Volatility interpretation
    content = content.replace(
        "**Volatility interpretation:**",
        f"**Volatility interpretation:** {w['vol_interpretation']}"
    )
    content = content.replace(
        "**Put/Call ratio trend this week:**",
        "**Put/Call ratio trend this week:** Elevated put buying early week; ratio improved by Friday as SpaceX/Micron catalysts lifted sentiment."
    )

    # Top Gainers of the Week
    gainers_rows = []
    for row in w["top_gainers"]:
        gainers_rows.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} |")
    gainers_section = "## Top Gainers of the Week (S&P 500)\n\n| Rank | Ticker | Company | Sector | Weekly % | Catalyst |\n|------|--------|---------|--------|----------|---------|\n"
    gainers_section += "\n".join(gainers_rows) + "\n"
    content = replace_section(content, "## Top Gainers of the Week (S&P 500)", gainers_section)

    # Top Losers of the Week
    losers_rows = []
    for row in w["top_losers"]:
        losers_rows.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} |")
    losers_section = "## Top Losers of the Week (S&P 500)\n\n| Rank | Ticker | Company | Sector | Weekly % | Catalyst |\n|------|--------|---------|--------|----------|---------|\n"
    losers_section += "\n".join(losers_rows) + "\n"
    content = replace_section(content, "## Top Losers of the Week (S&P 500)", losers_section)

    # Most market moving release
    content = content.replace(
        "**Most market-moving release this week:**",
        f"**Most market-moving release this week:** {w['market_moving_release']}"
    )
    content = content.replace(
        "**Data trend summary:**",
        f"**Data trend summary:** {w['data_trend_summary']}"
    )

    # Fed Watch Weekly
    fed_section = f"""## Fed Watch — Weekly

- **FOMC Activity This Week:** {w.get('fomc_activity', 'No FOMC meeting this week.')}
- **Current Fed Funds Rate:** 3.63% (target range 3.50–3.75%)
- **Fed Speakers This Week:** {w['fed_speakers']}
- **Key Quotes:** {w['fed_key_quotes']}
- **Rate Change Probability (CME FedWatch):** See daily reports for evolving estimates
- **Next FOMC Meeting:** June 16-17 (Week 1-2) / Late July 2026 (Week 3-4)
- **Fed Narrative Shift This Week (if any):** See market summary
"""
    content = replace_section(content, "## Fed Watch — Weekly", fed_section)

    # Sentiment Weekly
    first_day = list(DAILY.keys())[0]
    fg_score, fg_label = ("~28", "Fear")
    aaii_bulls, aaii_bears, aaii_neutral = ("34", "37", "29")
    sent_section = f"""## Sentiment Gauges — Weekly

- **CNN Fear & Greed Index (Friday):** {fg_score} — {fg_label} | Weekly trend: Volatile
- **AAII Sentiment (latest weekly):** Bulls {aaii_bulls}% | Bears {aaii_bears}% | Neutral {aaii_neutral}%
- **Reading:** Investor sentiment remained cautious throughout June. Bearish readings above 35% reflect macro uncertainty from FOMC hawkishness, elevated inflation, and geopolitical risk — despite strong AI earnings fundamentals.
"""
    content = replace_section(content, "## Sentiment Gauges — Weekly", sent_section)

    # Geopolitical Weekly
    geo_section = f"""## Geopolitical & Macro — Week in Review

- **Global:** {w['geopolitical_weekly']}
- **US Policy / Politics:** See global note above.
- **Energy Markets:** WTI Crude elevated early June (Strait of Hormuz disruption), declining in weeks 3-4 on Iran MOU.
- **Currency (DXY weekly %):** DXY range 119.0-120.4 throughout June; elevated due to Fed hawkishness and inflation.
- **Bond Market (10Y Yield — start / end / change):** See daily reports.
- **Credit Markets (HYG, LQD):** HYG modestly lower on rate hike fears; LQD slightly lower on duration pressure.
"""
    content = replace_section(content, "## Geopolitical & Macro — Week in Review", geo_section)

    # Next Week Calendar
    next_cal_rows = []
    for row in w.get("next_week_calendar", []):
        next_cal_rows.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
    next_section = "## Next Week — Economic Calendar Preview\n\n| Day | Event | Forecast | Previous | Importance |\n|-----|-------|----------|----------|------------|\n"
    next_section += "\n".join(next_cal_rows) + "\n\n"
    next_section += f"**Key earnings next week:** {w.get('next_earnings', 'TBD')}\n"
    next_section += f"**Key Fed speakers next week:** {w.get('next_fed_speakers', 'TBD')}\n"
    content = replace_section(content, "## Next Week — Economic Calendar Preview", next_section)

    # Market Summary, Opportunities, Risks
    ms_block = build_market_summary(w["market_summary"])
    content = replace_section(content, "## 1. Market Summary", ms_block)
    opp_block = build_opportunities(w["opportunities"])
    content = replace_section(content, "## 2. Opportunities", opp_block)
    risk_block = build_risks(w["risks"])
    content = replace_section(content, "## 3. Risks", risk_block)

    save(path, content)
    print(f"  ✓ Weekly filled: {path.name}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\n=== Filling qualitative sections in all investor reports ===\n")

    # Open reports
    print("--- Open Reports ---")
    for f in sorted((BASE / "Open").glob("Open_*.md")):
        if "Template" in f.name:
            continue
        # Parse date from filename: Open_06-01-26.md → 2026-06-01
        parts = f.stem.replace("Open_", "").split("-")
        date_str = f"20{parts[2]}-{parts[0]}-{parts[1]}"
        fill_open(f, date_str)

    # Close reports
    print("\n--- Close Reports ---")
    for f in sorted((BASE / "Close").glob("Close_*.md")):
        if "Template" in f.name:
            continue
        parts = f.stem.replace("Close_", "").split("-")
        date_str = f"20{parts[2]}-{parts[0]}-{parts[1]}"
        fill_close(f, date_str)

    # Weekly reports
    print("\n--- Weekly Reports ---")
    week_map = {
        "Weekly_06-01-26.md": "2026-06-01",
        "Weekly_06-08-26.md": "2026-06-08",
        "Weekly_06-15-26.md": "2026-06-15",
        "Weekly_06-22-26.md": "2026-06-22",
    }
    for fname, monday_str in week_map.items():
        path = BASE / "Weekly" / fname
        if path.exists():
            fill_weekly(path, monday_str)

    print("\n✓ All qualitative sections filled.")

if __name__ == "__main__":
    main()
