"""Shared look and feel: one stylesheet for the whole app plus small layout helpers.

All user-supplied text that ends up inside raw HTML must go through `esc()` first.
"""
from __future__ import annotations
import html
import streamlit as st

# Design tokens (kept in step with .streamlit/config.toml)
BG = "#0E1116"
SURFACE = "#151922"
SURFACE_2 = "#1B2029"
BORDER = "rgba(255,255,255,0.07)"
TEXT = "#E8EAEE"
MUTED = "#8A93A5"
ACCENT = "#D4AF63"
RED = "#FF453A"

_CSS = """
<style>
:root{
  --lv-bg:%(BG)s; --lv-surface:%(SURFACE)s; --lv-surface-2:%(SURFACE_2)s; --lv-border:%(BORDER)s;
  --lv-text:%(TEXT)s; --lv-muted:%(MUTED)s; --lv-accent:%(ACCENT)s; --lv-red:%(RED)s;
}
html, body, [class*="st-"], button, input, textarea, select { -webkit-font-smoothing: antialiased; }

/* ---------- chrome ---------- */
[data-testid="stDecoration"]{ display:none; }
[data-testid="stHeader"]{ background: transparent; }
[data-testid="stMainBlockContainer"], .block-container{ max-width: 1320px; padding-top: 2.6rem; padding-bottom: 4rem; }
h1{ font-weight: 650 !important; letter-spacing: -0.025em; font-size: 2rem !important; }
h2, h3{ font-weight: 600 !important; letter-spacing: -0.015em; }
hr{ border-color: var(--lv-border) !important; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{ border-right: 1px solid var(--lv-border); }
[data-testid="stSidebarNavSeparator"]{ display:none; }
[data-testid="stNavSectionHeader"], [data-testid="stSidebarNavItems"] header{
  font-size: .68rem !important; letter-spacing: .09em; text-transform: uppercase; color: var(--lv-muted) !important;
  font-weight: 600 !important; margin-top: .9rem !important; }
[data-testid="stSidebarNavLink"]{ padding: .2rem .65rem !important; margin: 1px 0 !important; border-radius: 8px !important;
  transition: background-color .12s ease; }
/* Bug fix: Streamlit renders the label as display:table-cell + overflow:hidden inside a flex row. WebKit (Safari,
   macOS webviews) collapses it to zero width on hover repaints, so the label of the active item vanished. */
[data-testid="stSidebarNavLink"] > span:last-child{
  display:block !important; flex: 1 1 auto; min-width: 0; color: var(--lv-muted) !important; font-weight: 500; }
[data-testid="stSidebarNavLink"]:hover{ background: rgba(255,255,255,0.05) !important; }
[data-testid="stSidebarNavLink"]:hover > span:last-child{ color: var(--lv-text) !important; }
[data-testid="stSidebarNavLink"][aria-current="page"]{ background: rgba(212,175,99,0.13) !important; }
[data-testid="stSidebarNavLink"][aria-current="page"] > span:last-child{ color: var(--lv-text) !important; font-weight: 600; }
[data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"]{ color: var(--lv-accent) !important; }
[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"]{ color: var(--lv-muted); }

.lv-user{ display:flex; align-items:center; gap:.65rem; padding:.55rem .6rem; border:1px solid var(--lv-border);
  border-radius:12px; background: var(--lv-surface); margin-bottom:.4rem; }
.lv-avatar{ width:32px; height:32px; border-radius:50%%; display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg,#D4AF63,#9C7B35); color:#14110A; font-weight:700; font-size:.8rem; flex-shrink:0; }
.lv-user-meta{ min-width:0; line-height:1.25; }
.lv-user-email{ font-size:.82rem; font-weight:600; color:var(--lv-text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.lv-user-plan{ font-size:.72rem; color:var(--lv-muted); }

/* ---------- surfaces ---------- */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]){ border-radius: 14px; }
[data-testid="stExpander"] details{ border-radius: 12px !important; border-color: var(--lv-border) !important; background: var(--lv-surface); }
[data-testid="stExpander"] summary{ font-weight: 500; }
[data-testid="stMetric"]{ background: var(--lv-surface); border:1px solid var(--lv-border); border-radius:14px; padding: 1rem 1.1rem; }
[data-testid="stMetricLabel"] p{ color: var(--lv-muted) !important; font-size:.78rem !important; text-transform: uppercase; letter-spacing:.06em; }
[data-testid="stMetricValue"]{ font-weight: 650; letter-spacing:-.02em; }
[data-testid="stAlert"]{ border-radius: 12px; }

/* ---------- controls ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, [data-testid="stPopover"] button{
  border-radius: 9px !important; font-weight: 500 !important; transition: all .12s ease; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"]{ color:#15120B !important; font-weight:600 !important; }
[data-testid="stTabs"] [role="tablist"]{ gap: 1.4rem; border-bottom: 1px solid var(--lv-border); }
[data-testid="stTabs"] button[role="tab"]{ padding: .55rem 0 !important; }
[data-testid="stTabs"] button[role="tab"] p{ font-weight: 500; font-size: .92rem; }
[data-testid="stTabs"] button[role="tab"][aria-selected="false"] p{ color: var(--lv-muted); }
[data-testid="stChatMessage"]{ background: transparent; }
[data-testid="stChatInput"] textarea{ font-size: .95rem; }

/* ---------- page header ---------- */
.lv-head{ margin: 0 0 1.4rem 0; }
.lv-eyebrow{ color: var(--lv-accent); font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; font-weight:600; margin-bottom:.35rem; }
.lv-title{ font-size: 2rem; font-weight: 650; letter-spacing: -.025em; line-height:1.15; color: var(--lv-text); margin:0; }
.lv-sub{ color: var(--lv-muted); font-size: .95rem; margin-top: .4rem; }

/* ---------- small building blocks ---------- */
.lv-card{ background: var(--lv-surface); border:1px solid var(--lv-border); border-radius:14px; padding:1rem 1.1rem; }
.lv-stat-label{ color:var(--lv-muted); font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; font-weight:600; }
.lv-stat-value{ font-size:1.65rem; font-weight:650; letter-spacing:-.02em; margin-top:.2rem; color:var(--lv-text); }
.lv-stat-note{ color:var(--lv-muted); font-size:.8rem; margin-top:.15rem; }
.lv-bar{ height:4px; border-radius:4px; background: rgba(255,255,255,.08); margin-top:.6rem; overflow:hidden; }
.lv-bar > i{ display:block; height:100%%; background: var(--lv-accent); border-radius:4px; }
.lv-section{ font-size:.78rem; letter-spacing:.08em; text-transform:uppercase; color:var(--lv-muted); font-weight:600; margin: 1.6rem 0 .6rem; }
.lv-list{ display:flex; flex-direction:column; }
.lv-item{ display:flex; gap:.75rem; align-items:flex-start; padding:.6rem 0; border-top:1px solid var(--lv-border); }
.lv-item:first-child{ border-top:none; }
.lv-item-dot{ width:8px; height:8px; border-radius:50%%; margin-top:.45rem; flex-shrink:0; }
.lv-item-main{ flex:1; min-width:0; }
.lv-item-title{ font-size:.92rem; color:var(--lv-text); font-weight:500; }
.lv-item-sub{ font-size:.78rem; color:var(--lv-muted); margin-top:.1rem; }
.lv-item-side{ font-size:.78rem; color:var(--lv-muted); white-space:nowrap; }
.lv-row-t{ font-size:.92rem; font-weight:500; color: var(--lv-text); }
.lv-row-d{ font-size:.82rem; color: var(--lv-muted); margin-top:.15rem; line-height:1.45; }
.lv-empty{ color: var(--lv-muted); font-size:.88rem; padding:.4rem 0; }
.lv-pill{ display:inline-block; font-size:.7rem; font-weight:600; padding:.12rem .5rem; border-radius:999px;
  background: rgba(212,175,99,.14); color: var(--lv-accent); letter-spacing:.02em; }
.lv-pill.red{ background: rgba(255,69,58,.15); color:#FF6961; }
.lv-pill.grey{ background: rgba(255,255,255,.07); color: var(--lv-muted); }
.lv-pill.amber{ background: rgba(255,159,10,.15); color:#FFB340; }
.lv-pill.green{ background: rgba(48,209,88,.14); color:#4CD964; }

/* ---------- case analysis: timeline and risk register ---------- */
.lv-tl{ position:relative; margin:.4rem 0 1rem .35rem; padding-left:1.4rem; border-left:2px solid var(--lv-border); }
.lv-tl-item{ position:relative; padding:.15rem 0 1.05rem; }
.lv-tl-item::before{ content:""; position:absolute; left:calc(-1.4rem - 6px); top:.42rem; width:10px; height:10px;
  border-radius:50%%; background: var(--lv-muted); box-shadow: 0 0 0 3px var(--lv-bg); }
.lv-tl-item.legal::before{ background: var(--lv-accent); }
.lv-tl-item.deadline::before{ background: var(--lv-red); }
.lv-tl-date{ font-size:.74rem; letter-spacing:.06em; text-transform:uppercase; color:var(--lv-muted); font-weight:600; }
.lv-tl-ev{ font-size:.95rem; color:var(--lv-text); font-weight:500; margin-top:.1rem; line-height:1.4; }
.lv-tl-sig{ font-size:.83rem; color:var(--lv-muted); margin-top:.2rem; line-height:1.45; }
.lv-tl-src{ font-size:.72rem; color:var(--lv-muted); margin-top:.25rem; opacity:.8; }
.lv-risk{ background: var(--lv-surface); border:1px solid var(--lv-border); border-left:3px solid var(--lv-muted);
  border-radius:12px; padding:.85rem 1rem; margin-bottom:.7rem; }
.lv-risk.high{ border-left-color:#FF453A; } .lv-risk.medium{ border-left-color:#FF9F0A; } .lv-risk.low{ border-left-color:#30D158; }
.lv-risk-h{ display:flex; gap:.5rem; align-items:center; flex-wrap:wrap; }
.lv-risk-t{ font-weight:600; font-size:.95rem; color:var(--lv-text); margin-right:auto; }
.lv-risk-d{ font-size:.87rem; color:var(--lv-text); margin-top:.45rem; line-height:1.5; }
.lv-risk-m{ font-size:.83rem; color:var(--lv-muted); margin-top:.35rem; line-height:1.45; }
.lv-risk-m b{ color: var(--lv-text); font-weight:600; }
.lv-matrix{ display:grid; grid-template-columns: auto repeat(3, 1fr); gap:4px; font-size:.75rem; max-width:360px; }
.lv-matrix div{ padding:.45rem .3rem; text-align:center; border-radius:6px; color:var(--lv-muted); }
.lv-matrix .cell{ font-weight:700; font-size:.95rem; color:var(--lv-text); }
</style>
""" % dict(BG=BG, SURFACE=SURFACE, SURFACE_2=SURFACE_2, BORDER=BORDER, TEXT=TEXT, MUTED=MUTED, ACCENT=ACCENT, RED=RED)


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


def html_block(markup: str):
    """Render trusted markup. Collapses indentation so Markdown never turns it into a code block."""
    st.markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", eyebrow: str = ""):
    html_block(f"""<div class="lv-head">
        {f'<div class="lv-eyebrow">{esc(eyebrow)}</div>' if eyebrow else ''}
        <div class="lv-title">{esc(title)}</div>
        {f'<div class="lv-sub">{esc(subtitle)}</div>' if subtitle else ''}
    </div>""")


def section(label: str):
    html_block(f'<div class="lv-section">{esc(label)}</div>')


def stat(label: str, value: str, note: str = "", progress: float | None = None) -> str:
    bar = f'<div class="lv-bar"><i style="width:{max(0, min(1, progress)) * 100:.0f}%"></i></div>' if progress is not None else ""
    return (f'<div class="lv-card"><div class="lv-stat-label">{esc(label)}</div>'
            f'<div class="lv-stat-value">{esc(value)}</div>'
            f'{f"<div class=lv-stat-note>{esc(note)}</div>" if note else ""}{bar}</div>')


def item(title: str, sub: str = "", side: str = "", dot: str = "") -> str:
    d = f'<span class="lv-item-dot" style="background:{dot}"></span>' if dot else ""
    return (f'<div class="lv-item">{d}<div class="lv-item-main"><div class="lv-item-title">{esc(title)}</div>'
            f'{f"<div class=lv-item-sub>{esc(sub)}</div>" if sub else ""}</div>'
            f'{f"<div class=lv-item-side>{esc(side)}</div>" if side else ""}</div>')


def initials(email: str) -> str:
    name = (email or "?").split("@")[0]
    parts = [p for p in name.replace("_", ".").replace("-", ".").split(".") if p]
    return ((parts[0][0] + (parts[1][0] if len(parts) > 1 else "")) if parts else "?").upper()
