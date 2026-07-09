#!/usr/bin/env python3
"""
report_pdf.py — GlobalMarkets Investor report renderer (v2 design system)

Parses a report markdown file into structured sections generically (works
across open/close/weekly/monthly, whose section sets differ), classifies
each section by header keyword + content shape, and renders it as a styled
print PDF via headless Chromium (Playwright), replacing xhtml2pdf.

Public interface preserved for compatibility with post_discord.py / run_report.sh:
    convert(md_path: Path, out_path: Path | None = None) -> Path
"""

import argparse
import math
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
FONTS = BASE / "fonts"

# ---------------------------------------------------------------------------
# Palette (single fixed light theme — a PDF has no viewer theme toggle)
# ---------------------------------------------------------------------------

INK = (11, 31, 59)          # #0B1F3B
INK_SOFT = (71, 83, 107)    # #47536B
INK_FAINT = (124, 138, 160) # #7C8AA0
SURFACE = (255, 255, 255)
SURFACE_2 = (245, 247, 251)
BORDER = "#DCE3ED"
ACCENT = "#8A6416"
ACCENT_STRONG = "#6B4D0F"
ACCENT_TINT = "#F1E4C2"
GAIN = (30, 122, 70)        # #1E7A46
GAIN_TINT = (225, 241, 230) # #E1F1E6
LOSS = (168, 50, 50)        # #A83232
LOSS_TINT = (248, 228, 225) # #F8E4E1


def _rgb(t):
    return f"rgb({t[0]},{t[1]},{t[2]})"


def _lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def pct_cell_style(pct):
    """Return (background_css, color_css, bold) for a heatmap cell given a % value."""
    clamped = max(-20.0, min(20.0, pct))
    t = math.sqrt(abs(clamped) / 20.0) if clamped else 0.0
    if pct > 0.05:
        bg = _lerp(SURFACE, GAIN_TINT, t)
        fg = _rgb(GAIN) if t > 0.35 else _rgb(GAIN)
    elif pct < -0.05:
        bg = _lerp(SURFACE, LOSS_TINT, t)
        fg = _rgb(LOSS) if t > 0.35 else _rgb(LOSS)
    else:
        bg = SURFACE
        fg = _rgb(INK_FAINT)
    bold = abs(pct) >= 5
    return _rgb(bg), fg, bold


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

NUM_RE = re.compile(r'^[+\-−]?[\d,]+\.?\d*%?$')


def parse_pct(text):
    """Parse a percentage cell like '+13.09%', '−17.85%', '—' -> float or None."""
    text = text.strip().replace('−', '-')
    if not text or text in ('-', '—', 'N/A', 'n/a'):
        return None
    m = re.match(r'^([+\-]?\d+\.?\d*)%$', text)
    if not m:
        return None
    return float(m.group(1))


def is_placeholder_row(cells):
    """True if every cell is blank/dash — the padding rows in Top Gainers/Losers etc."""
    for c in cells:
        c = c.strip().replace('−', '-')
        if c and c not in ('-', '—', ''):
            return False
    return True


def md_inline(text):
    """Minimal inline markdown -> HTML: **bold**, then escape done already upstream."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return text


def esc(text):
    return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


class Table:
    def __init__(self, headers, rows):
        self.headers = headers
        self.rows = rows  # list of list[str]

    @property
    def pct_cols(self):
        return [i for i, h in enumerate(self.headers) if '%' in h]


class Node:
    """One markdown section (H2 or H3) with its raw content parsed into parts."""
    def __init__(self, level, title):
        self.level = level
        self.title = title
        self.bullets = []       # list of raw bullet strings (markdown, may contain **bold**)
        self.bold_lines = []    # list of (label, value) from "**Label:** value" non-bullet lines
        self.paragraphs = []    # plain paragraph strings
        self.tables = []        # list of Table
        self.children = []      # nested Node (H3 under this H2)


def parse_markdown(text):
    lines = text.split('\n')
    title = ""
    meta = []  # (label, value)
    i = 0
    # H1 title
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith('# '):
            title = line[2:].strip()
            i += 1
            break
        i += 1
    # meta bold lines until first '## ' or '---'
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('## ') or line == '---':
            break
        m = re.match(r'^\*\*(.+?):\*\*\s*(.*)$', line)
        if m:
            meta.append((m.group(1), m.group(2)))
        i += 1

    top_nodes = []
    cur_h2 = None
    cur_h3 = None

    def flush_table(buf, target):
        if len(buf) >= 2:
            header_cells = [c.strip() for c in buf[0].strip().strip('|').split('|')]
            data_rows = []
            for row_line in buf[2:]:
                cells = [c.strip() for c in row_line.strip().strip('|').split('|')]
                if len(cells) == len(header_cells):
                    data_rows.append(cells)
            target.tables.append(Table(header_cells, data_rows))
        buf.clear()

    table_buf = []

    def current_target():
        return cur_h3 if cur_h3 is not None else cur_h2

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith('|'):
            table_buf.append(stripped)
            i += 1
            continue
        elif table_buf:
            flush_table(table_buf, current_target())

        if stripped == '---':
            pass
        elif stripped.startswith('### '):
            cur_h3 = Node(3, stripped[4:].strip())
            if cur_h2 is not None:
                cur_h2.children.append(cur_h3)
            i += 1
            continue
        elif stripped.startswith('## '):
            cur_h2 = Node(2, stripped[3:].strip())
            cur_h3 = None
            top_nodes.append(cur_h2)
            i += 1
            continue
        elif stripped.startswith('- '):
            target = current_target()
            if target is not None:
                target.bullets.append(stripped[2:].strip())
        elif re.match(r'^\*\*(.+?):\*\*\s*(.*)$', stripped):
            m = re.match(r'^\*\*(.+?):\*\*\s*(.*)$', stripped)
            target = current_target()
            if target is not None:
                target.bold_lines.append((m.group(1), m.group(2)))
        elif stripped and not stripped.startswith('#'):
            target = current_target()
            if target is not None:
                target.paragraphs.append(stripped)
        i += 1

    if table_buf:
        flush_table(table_buf, current_target())

    return title, meta, top_nodes


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify(node: Node) -> str:
    t = node.title.lower()
    if re.search(r'market tone|executive summary', t):
        return 'hero'
    if re.search(r'sentiment gauges|month-end sentiment', t):
        return 'sentiment'
    if re.search(r'gainers|losers', t):
        return 'movers'
    if re.search(r'analyst actions', t):
        return 'analyst'
    if re.search(r'market summary', t):
        return 'summary'
    if re.search(r'opportunit', t):
        return 'opportunities'
    if re.search(r'\brisks\b', t):
        return 'risks'
    return 'generic'


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def render_heatmap_table(table: Table, title=None):
    pct_idx = set(table.pct_cols)
    out = ['<div class="tbl-wrap">']
    if title:
        out.append(f'<div class="tbl-title">{esc(title)}</div>')
    out.append('<table class="heat"><thead><tr>')
    for h in table.headers:
        out.append(f'<th>{esc(h)}</th>')
    out.append('</tr></thead><tbody>')
    for row in table.rows:
        if is_placeholder_row(row):
            continue
        out.append('<tr>')
        for ci, cell in enumerate(row):
            if ci in pct_idx:
                val = parse_pct(cell)
                if val is None:
                    out.append(f'<td class="num">{esc(cell)}</td>')
                else:
                    bg, fg, bold = pct_cell_style(val)
                    w = '600' if bold else '400'
                    out.append(
                        f'<td class="num" style="background:{bg};color:{fg};font-weight:{w};">{esc(cell)}</td>'
                    )
            elif ci == 0:
                out.append(f'<td class="label">{esc(cell)}</td>')
            else:
                out.append(f'<td class="num">{esc(cell)}</td>')
        out.append('</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


def render_plain_table(table: Table, title=None):
    out = ['<div class="tbl-wrap">']
    if title:
        out.append(f'<div class="tbl-title">{esc(title)}</div>')
    out.append('<table class="plain"><thead><tr>')
    for h in table.headers:
        out.append(f'<th>{esc(h)}</th>')
    out.append('</tr></thead><tbody>')
    rows_out = 0
    for row in table.rows:
        if is_placeholder_row(row):
            continue
        rows_out += 1
        out.append('<tr>')
        for ci, cell in enumerate(row):
            cls = 'label' if ci == 0 else 'num'
            out.append(f'<td class="{cls}">{md_inline(esc(cell)) or "&mdash;"}</td>')
        out.append('</tr>')
    out.append('</tbody></table></div>')
    if rows_out == 0:
        return None
    return ''.join(out)


def render_bullets(bullets):
    if not bullets:
        return ''
    items = ''.join(f'<li>{md_inline(esc(b))}</li>' for b in bullets)
    return f'<ul class="plain-list">{items}</ul>'


def render_bold_lines(bold_lines):
    if not bold_lines:
        return ''
    out = ['<div class="kv-list">']
    for label, value in bold_lines:
        out.append(f'<div class="kv-row"><span class="kv-label">{esc(label)}</span>'
                    f'<span class="kv-value">{md_inline(esc(value))}</span></div>')
    out.append('</div>')
    return ''.join(out)


def render_generic_node(node: Node, heading_tag='h2'):
    out = [f'<div class="generic-section"><{heading_tag} class="section-title">{esc(node.title)}</{heading_tag}>']
    out.append(render_bold_lines(node.bold_lines))
    out.append(render_bullets(node.bullets))
    for p in node.paragraphs:
        out.append(f'<p class="prose">{md_inline(esc(p))}</p>')
    for t in node.tables:
        if t.pct_cols:
            out.append(render_heatmap_table(t))
        else:
            rendered = render_plain_table(t)
            if rendered:
                out.append(rendered)
    for child in node.children:
        out.append(render_generic_node(child, heading_tag='h3'))
    out.append('</div>')
    return ''.join(out)


MOVER_KEYWORDS = {
    'ticker': 'ticker', 'company': 'company', 'catalyst': 'catalyst',
    'volume': 'volume', 'volume vs avg': 'volume',
}


def _find_col(headers, *keywords):
    for i, h in enumerate(headers):
        hl = h.lower()
        for kw in keywords:
            if kw in hl:
                return i
    return None


def render_mover_group(title, table: Table, show_heading=True):
    ticker_i = _find_col(table.headers, 'ticker')
    company_i = _find_col(table.headers, 'company')
    catalyst_i = _find_col(table.headers, 'catalyst')
    volume_i = _find_col(table.headers, 'volume')
    pct_candidates = table.pct_cols
    pct_i = pct_candidates[0] if pct_candidates else None

    cards = []
    for row in table.rows:
        if is_placeholder_row(row):
            continue
        ticker = row[ticker_i] if ticker_i is not None else ''
        company = row[company_i] if company_i is not None and company_i < len(row) else ''
        catalyst = row[catalyst_i] if catalyst_i is not None and catalyst_i < len(row) else ''
        volume = row[volume_i] if volume_i is not None and volume_i < len(row) else ''
        pct_val = parse_pct(row[pct_i]) if pct_i is not None and pct_i < len(row) else None
        pct_text = row[pct_i] if pct_i is not None and pct_i < len(row) else ''
        cls = 'pos' if (pct_val or 0) > 0 else ('neg' if (pct_val or 0) < 0 else '')
        cards.append(
            '<div class="mover-card">'
            '<div class="mover-left">'
            f'<span class="mover-ticker">{esc(ticker)}</span>'
            + (f'<span class="mover-name">{esc(company)}</span>' if company and company != '—' else '')
            + (f'<p class="mover-catalyst">{md_inline(esc(catalyst))}</p>' if catalyst and catalyst != '—' else '')
            + '</div>'
            f'<div class="mover-right"><span class="mover-pct {cls}">{esc(pct_text)}</span>'
            + (f'<span class="mover-vol">{esc(volume)}</span>' if volume and volume != '—' else '')
            + '</div></div>'
        )
    heading = f'<h3>{esc(title)}</h3>' if show_heading else ''
    if not cards:
        return f'<div class="mover-group">{heading}<p class="muted-line">None reported.</p></div>'
    return f'<div class="mover-group">{heading}{"".join(cards)}</div>'


def render_movers_node(node: Node):
    out = [f'<div class="movers-section"><h2 class="section-title">{esc(node.title)}</h2>']
    if node.tables:
        out.append(render_mover_group(node.title, node.tables[0], show_heading=False))
    for child in node.children:
        if child.tables:
            out.append(render_mover_group(child.title, child.tables[0], show_heading=True))
        else:
            out.append(render_generic_node(child, heading_tag='h3'))
    out.append('</div>')
    return ''.join(out)


def render_analyst_node(node: Node):
    out = [f'<div class="analyst-section"><h2 class="section-title">{esc(node.title)}</h2>']

    def action_cards(table: Table, kind):
        ticker_i = _find_col(table.headers, 'ticker')
        company_i = _find_col(table.headers, 'company')
        from_i = _find_col(table.headers, 'from')
        to_i = None
        for i, h in enumerate(table.headers):
            if h.strip().lower() == 'to':
                to_i = i
        firm_i = _find_col(table.headers, 'firm')
        cards = []
        for row in table.rows:
            if is_placeholder_row(row):
                continue
            ticker = row[ticker_i] if ticker_i is not None and ticker_i < len(row) else ''
            if not ticker or ticker == '—':
                continue
            company = row[company_i] if company_i is not None and company_i < len(row) else ''
            frm = row[from_i] if from_i is not None and from_i < len(row) else ''
            to = row[to_i] if to_i is not None and to_i < len(row) else ''
            firm = row[firm_i] if firm_i is not None and firm_i < len(row) else ''
            flag_cls = 'gain' if kind == 'Upgrade' else 'loss'
            company_html = f' &middot; {esc(company)}' if company and company != '—' else ''
            firm_html = f' <span class="analyst-firm">({esc(firm)})</span>' if firm and firm != '—' else ''
            cards.append(
                f'<div class="analyst-card {flag_cls}"><div>'
                f'<span class="analyst-ticker">{esc(ticker)}</span>{company_html}'
                f'<div class="analyst-move">{esc(frm)} &rarr; {esc(to)}{firm_html}</div>'
                f'</div><span class="analyst-flag {flag_cls}">{kind}</span></div>'
            )
        return cards

    all_cards = []
    for child in node.children:
        kind = 'Upgrade' if 'upgrade' in child.title.lower() else 'Downgrade'
        if child.tables:
            all_cards.extend(action_cards(child.tables[0], kind))
    if node.tables:
        all_cards.extend(action_cards(node.tables[0], 'Downgrade'))

    if all_cards:
        out.extend(all_cards)
    else:
        out.append('<p class="muted-line">No analyst actions reported.</p>')
    out.append('</div>')
    return ''.join(out)


def render_hero_node(node: Node):
    overall = ''
    for label, value in node.bold_lines:
        if label.strip().lower() == 'overall':
            overall = value
    bullets = list(node.bullets)
    thesis = bullets.pop(0) if bullets else ''
    out = ['<div class="hero">']
    if overall:
        out.append(f'<span class="badge badge-tone">Overall: {esc(overall)}</span>')
    if thesis:
        out.append(f'<p class="thesis">{md_inline(esc(thesis))}</p>')
    if bullets:
        out.append(render_bullets(bullets))
    for p in node.paragraphs:
        out.append(f'<p class="thesis">{md_inline(esc(p))}</p>' if not thesis else f'<p class="prose">{md_inline(esc(p))}</p>')
        thesis = thesis or p
    out.append('</div>')
    return ''.join(out)


SENTIMENT_WORDS = [
    (r'extreme\s*fear', 8), (r'extreme\s*greed', 92),
    (r'neutral\s*(to|[-–])\s*fear|fear\s*(to|[-–])\s*neutral', 34),
    (r'neutral\s*(to|[-–])\s*greed|greed\s*(to|[-–])\s*neutral', 66),
    (r'\bfear\b', 22), (r'\bgreed\b', 78), (r'\bneutral\b', 50),
]


def extract_fg_number(text):
    """Extract an explicit 'CNN Fear & Greed ... ~58 (Greed)' style numeric
    reading. Deliberately only called on the CNN F&G bullet itself, never on
    freeform prose — a paragraph can easily contain an unrelated '16.90
    (moderate)' (e.g. a VIX level) that would falsely match a looser pattern.
    """
    m = re.search(r'fear\s*&\s*greed[^~\d]*~?\s*(\d{1,3})\s*(?:/\s*100)?\s*\((\w[\w\s]*?)\)', text, re.I)
    if m:
        try:
            v = int(m.group(1))
            if 0 <= v <= 100:
                return v, f"{v} &middot; {m.group(2).strip().title()}"
        except ValueError:
            pass
    return None, None


def keyword_bucket(text):
    low = text.lower()
    for pattern, pos in SENTIMENT_WORDS:
        m = re.search(pattern, low)
        if m:
            return pos, m.group(0).title().replace(' To ', ' – ')
    return None, None


def render_sentiment_node(node: Node):
    out = [f'<div class="sentiment-section"><h2 class="section-title">{esc(node.title)}</h2>']
    reading_text = ''
    for b in node.bullets:
        m = re.match(r'^\*\*Reading:?\*\*\s*(.*)$', b)
        if m:
            reading_text = m.group(1)
    cnn_text = ''
    for b in node.bullets:
        if re.search(r'fear\s*&\s*greed', b, re.I):
            cnn_text = b
    # Prefer a real numeric CNN F&G reading; then keyword-bucket the
    # synthesized "Reading:" conclusion; only keyword-scan the CNN label
    # itself last, since an unavailable value there ("— data not available")
    # can contain the word "Fear" purely as part of the index's own name.
    pos, label = (None, None)
    if cnn_text:
        pos, label = extract_fg_number(cnn_text)
    if pos is None and reading_text:
        pos, label = keyword_bucket(reading_text)
    if pos is None and cnn_text:
        pos, label = keyword_bucket(cnn_text)
    if pos is not None:
        out.append(
            '<div class="meter-block">'
            f'<div class="sentiment-label"><span>Sentiment</span><b>{label}</b></div>'
            f'<div class="meter-track"><div class="meter-marker" style="left:{pos}%;"></div></div>'
            '<div class="meter-ends"><span>Fear</span><span>Greed</span></div>'
            '</div>'
        )
    out.append(render_bullets(node.bullets))
    out.append('</div>')
    return ''.join(out)


def render_opp_risk_node(node: Node, kind):
    cls = 'opp' if kind == 'opportunities' else 'risk'
    out = [f'<h2 class="section-title">{esc(node.title)}</h2>']
    if not node.bullets:
        out.append(render_generic_node(node, heading_tag='h3'))
        return ''.join(out)
    for b in node.bullets:
        m = re.match(r'^\*\*(.+?):\*\*\s*(.*)$', b)
        if m:
            lead, body = m.group(1), m.group(2)
            out.append(
                f'<div class="item {cls}"><span class="item-lead">{esc(lead)}</span>'
                f'<span class="item-body">{md_inline(esc(body))}</span></div>'
            )
        else:
            out.append(f'<div class="item {cls}"><span class="item-body">{md_inline(esc(b))}</span></div>')
    return ''.join(out)


def render_summary_node(node: Node):
    out = [f'<h2 class="section-title">{esc(node.title)}</h2>']
    for p in node.paragraphs:
        out.append(f'<p class="prose">{md_inline(esc(p))}</p>')
    if node.bullets:
        out.append(render_bullets(node.bullets))
    return ''.join(out)


# ---------------------------------------------------------------------------
# CSS + font embedding
# ---------------------------------------------------------------------------

def _font_face(family, weight, style, filename):
    path = FONTS / filename
    data = path.read_bytes()
    import base64
    b64 = base64.b64encode(data).decode('ascii')
    return (f'@font-face{{font-family:"{family}";font-weight:{weight};'
            f'font-style:{style};src:url(data:font/ttf;base64,{b64}) format("truetype");}}')


def build_css():
    faces = [
        _font_face('PSans', 400, 'normal', 'PlexSans-Regular.ttf'),
        _font_face('PSansSemi', 600, 'normal', 'PlexSans-SemiBold.ttf'),
        _font_face('PMono', 400, 'normal', 'PlexMono-Regular.ttf'),
        _font_face('PMonoMed', 500, 'normal', 'PlexMono-Medium.ttf'),
        _font_face('PMonoSemi', 600, 'normal', 'PlexMono-SemiBold.ttf'),
        _font_face('NNews', 500, 'normal', 'Newsreader-Medium.ttf'),
        _font_face('NNewsSemi', 600, 'normal', 'Newsreader-SemiBold.ttf'),
        _font_face('NNewsItalic', 500, 'italic', 'Newsreader-MediumItalic.ttf'),
    ]
    return '\n'.join(faces) + '''
@page { size: letter; margin: 0.75in 0.7in 0.7in 0.7in; }
* { box-sizing: border-box; }
body { margin:0; font-family:'PSans',sans-serif; font-size:9.5pt; line-height:1.55; color:#0B1F3B; }
.mono { font-family:'PMono',monospace; }

.masthead { border-bottom:2px solid #8A6416; padding-bottom:10px; margin-bottom:14px; }
.eyebrow { font-family:'PSansSemi',sans-serif; font-size:8pt; letter-spacing:0.08em; text-transform:uppercase; color:#8A6416; margin:0 0 4px; }
h1.title { font-family:'NNewsSemi',serif; font-size:22pt; margin:0 0 8px; color:#0B1F3B; }
.masthead-meta { font-size:8.5pt; color:#47536B; }
.badge { display:inline-block; padding:3px 10px; border-radius:100px; font-size:8pt; font-family:'PSansSemi',sans-serif; border:1px solid #DCE3ED; }
.badge-tone { color:#6B4D0F; background:#F1E4C2; border-color:transparent; }
.badge-status { color:#47536B; background:#F5F7FB; }

.section-title { font-family:'PSansSemi',sans-serif; font-size:9pt; letter-spacing:0.06em; text-transform:uppercase; color:#47536B; margin:16px 0 8px; page-break-after:avoid; }
h3.section-title { font-size:8pt; margin:10px 0 6px; }

.hero { background:#F5F7FB; border-radius:8px; padding:12px 16px; margin-bottom:8px; page-break-inside:avoid; }
.thesis { font-family:'NNewsItalic',serif; font-style:italic; font-size:12.5pt; line-height:1.4; margin:8px 0 10px; }
.prose { font-size:9.3pt; color:#334; line-height:1.65; margin:0 0 8px; color:#333f52; }

ul.plain-list { margin:6px 0; padding-left:16px; }
ul.plain-list li { font-size:8.8pt; color:#3d4a63; margin-bottom:5px; line-height:1.5; }

.kv-list { margin:4px 0 8px; }
.kv-row { display:flex; gap:6px; font-size:8.8pt; margin-bottom:4px; }
.kv-label { font-family:'PSansSemi',sans-serif; color:#0B1F3B; flex-shrink:0; }
.kv-value { color:#47536B; }

.tbl-wrap { margin:6px 0 12px; }
.tbl-title { font-family:'PSansSemi',sans-serif; font-size:8pt; color:#7C8AA0; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px; }
table { border-collapse:collapse; width:100%; font-size:8pt; }
table.heat th, table.heat td, table.plain th, table.plain td { padding:5px 8px; text-align:right; border-bottom:1px solid #DCE3ED; }
table th { font-family:'PSansSemi',sans-serif; font-size:7.3pt; text-transform:uppercase; letter-spacing:0.03em; color:#7C8AA0; text-align:right; }
table td.label, table th:first-child { text-align:left; }
table td.label { font-family:'PSansSemi',sans-serif; font-size:8pt; }
table td.num { font-family:'PMono',monospace; }
tr:nth-child(even) td.label, tr:nth-child(even) td.num:not([style]) { background:#F9FAFC; }

.movers-section, .analyst-section { page-break-inside:avoid; margin-bottom:6px; }
.mover-group { margin-bottom:10px; }
.mover-group h3 { font-family:'PSansSemi',sans-serif; font-size:8.5pt; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 6px; }
.mover-card { display:flex; justify-content:space-between; gap:10px; border:1px solid #DCE3ED; border-radius:8px; padding:8px 12px; margin-bottom:6px; page-break-inside:avoid; }
.mover-ticker { font-family:'PMonoSemi',monospace; font-weight:600; font-size:9.5pt; display:block; }
.mover-name { font-size:7.8pt; color:#7C8AA0; display:block; }
.mover-catalyst { font-size:7.6pt; color:#47536B; margin:4px 0 0; max-width:340px; }
.mover-right { text-align:right; flex-shrink:0; }
.mover-pct { font-family:'PMonoSemi',monospace; font-weight:600; font-size:9.5pt; }
.mover-vol { display:block; font-size:7.3pt; color:#7C8AA0; }
.pos { color:#1E7A46; } .neg { color:#A83232; }

.analyst-card { display:flex; justify-content:space-between; align-items:center; gap:10px; border-radius:8px; padding:8px 12px; margin-bottom:6px; page-break-inside:avoid; }
.analyst-card.gain { background:#E1F1E6; } .analyst-card.loss { background:#F8E4E1; }
.analyst-ticker { font-family:'PMonoSemi',monospace; font-weight:600; }
.analyst-move { font-size:8.3pt; color:#47536B; margin-top:1px; }
.analyst-firm { color:#7C8AA0; }
.analyst-flag { font-family:'PSansSemi',sans-serif; font-size:7.3pt; text-transform:uppercase; letter-spacing:0.04em; }
.analyst-flag.gain { color:#1E7A46; } .analyst-flag.loss { color:#A83232; }
.muted-line { font-size:8.5pt; color:#7C8AA0; font-style:italic; }

.item { padding:8px 12px; border-radius:8px; margin-bottom:6px; page-break-inside:avoid; }
.item.opp { background:#E1F1E6; } .item.risk { background:#F8E4E1; }
.item-lead { font-family:'NNewsItalic',serif; font-style:italic; font-size:9.3pt; display:block; margin-bottom:2px; }
.item.opp .item-lead { color:#1E7A46; } .item.risk .item-lead { color:#A83232; }
.item-body { font-size:8.3pt; color:#3d4a63; line-height:1.55; }

.sentiment-section { page-break-inside:avoid; }
.meter-block { max-width:260px; margin:4px 0 10px; }
.sentiment-label { display:flex; justify-content:space-between; font-size:7.3pt; text-transform:uppercase; letter-spacing:0.04em; color:#7C8AA0; margin-bottom:4px; }
.sentiment-label b { font-family:'PSansSemi',sans-serif; color:#0B1F3B; text-transform:none; letter-spacing:0; }
.meter-track { position:relative; height:5px; border-radius:4px; background:linear-gradient(90deg,#A83232 0%,#F5F7FB 50%,#1E7A46 100%); }
.meter-marker { position:absolute; top:50%; width:10px; height:10px; margin-left:-5px; background:#fff; border:2px solid #0B1F3B; border-radius:50%; transform:translateY(-50%); }
.meter-ends { display:flex; justify-content:space-between; font-size:6.8pt; color:#7C8AA0; margin-top:3px; text-transform:uppercase; }

.generic-section { margin-bottom:4px; }
.footer-note { font-size:7.3pt; color:#9aa5b8; text-align:center; margin-top:18px; padding-top:6px; border-top:1px solid #DCE3ED; }
'''


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def render_html(md_text: str) -> str:
    title, meta, nodes = parse_markdown(md_text)
    meta_dict = dict(meta)

    parts = ['<div class="masthead"><p class="eyebrow">GlobalMarkets Investor</p>']
    parts.append(f'<h1 class="title">{esc(title)}</h1>')
    status = meta_dict.get('Market Status', '')
    generated = meta_dict.get('Generated', '')
    meta_bits = []
    if generated:
        meta_bits.append(f'Generated {esc(generated)}')
    if status:
        meta_bits.append(f'<span class="badge badge-status">{esc(status)}</span>')
    parts.append(f'<div class="masthead-meta">{" &middot; ".join(meta_bits)}</div></div>')

    for node in nodes:
        kind = classify(node)
        if kind == 'hero':
            parts.append(render_hero_node(node))
        elif kind == 'sentiment':
            parts.append(render_sentiment_node(node))
        elif kind == 'movers':
            parts.append(render_movers_node(node))
        elif kind == 'analyst':
            parts.append(render_analyst_node(node))
        elif kind == 'summary':
            parts.append(render_summary_node(node))
        elif kind == 'opportunities':
            parts.append(render_opp_risk_node(node, 'opportunities'))
        elif kind == 'risks':
            parts.append(render_opp_risk_node(node, 'risks'))
        else:
            parts.append(render_generic_node(node))

    parts.append(
        '<p class="footer-note">This report is for informational purposes only and does not '
        'constitute investment advice. All market data is sourced from publicly available '
        'information. Past performance is not indicative of future results. Please consult a '
        'licensed financial advisor before making investment decisions.</p>'
    )

    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{build_css()}</style></head><body>{"".join(parts)}</body></html>'


def convert(md_path: Path, out_path: Path = None) -> Path:
    md_path = Path(md_path)
    if out_path is None:
        out_path = md_path.with_suffix('.pdf')
    out_path = Path(out_path)

    md_text = md_path.read_text(encoding='utf-8')
    html = render_html(md_text)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until='load')
        page.pdf(
            path=str(out_path),
            format='Letter',
            print_background=True,
            margin={'top': '0in', 'bottom': '0in', 'left': '0in', 'right': '0in'},
        )
        browser.close()
    return out_path


def main():
    parser = argparse.ArgumentParser(description='Convert market report markdown to PDF (v2)')
    parser.add_argument('files', nargs='+')
    parser.add_argument('--out', default=None)
    args = parser.parse_args()
    if args.out and len(args.files) > 1:
        print('[ERROR] --out can only be used with a single input file.')
        sys.exit(1)
    ok = True
    for f in args.files:
        p = Path(f)
        out = Path(args.out) if args.out else None
        try:
            result = convert(p, out)
            print(f'✓ {p.name} → {result}')
        except Exception as e:
            print(f'✗ {p.name} failed: {e}')
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
