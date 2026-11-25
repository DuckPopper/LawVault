"""Shared look and feel: one stylesheet for the whole app plus small layout helpers.

All user-supplied text that ends up inside raw HTML must go through `esc()` first.
"""
from __future__ import annotations
import html
import streamlit as st
from i18n import t

# Design tokens. Two themes share one stylesheet; the tokens below are swapped per user (users.theme).
THEMES = {
    "dark": dict(BG="#0c1410", BG2="#183a36", BG3="#1c4144", GLOW="#2f7f88",
                 SURFACE="rgba(148,220,210,0.06)", SURFACE_2="rgba(148,220,210,0.12)",
                 BORDER="rgba(148,220,210,0.16)", EDGE="rgba(148,220,210,0.24)",
                 TEXT="#e6fbf7", MUTED="rgba(230,251,247,0.62)", ACCENT="#5bc5cf", ON_ACCENT="#0c1410",
                 HOVER="rgba(148,220,210,0.10)", INPUT="rgba(12,20,16,0.55)", POP="#112019",
                 SHADE="rgba(0,0,0,0.35)", SCHEME="dark", RED="#FF6B63", AMBER="#FFB340", GREEN="#4CD98A",
                 PILL_BG="rgba(91,197,207,0.16)"),
    "light": dict(BG="#e9faf7", BG2="#94dcd2", BG3="#bff0e9", GLOW="#5bc5cf",
                  SURFACE="rgba(255,255,255,0.55)", SURFACE_2="rgba(255,255,255,0.78)",
                  BORDER="rgba(31,47,37,0.12)", EDGE="rgba(255,255,255,0.95)",
                  TEXT="#1f2f25", MUTED="rgba(31,47,37,0.64)", ACCENT="#306761", ON_ACCENT="#ffffff",
                  HOVER="rgba(48,103,97,0.09)", INPUT="rgba(255,255,255,0.72)", POP="#f4fffd",
                  SHADE="rgba(31,47,37,0.14)", SCHEME="light", RED="#C2362E", AMBER="#B4690E", GREEN="#1C7A4B",
                  PILL_BG="rgba(48,103,97,0.13)"),
}
DEFAULT_THEME = "dark"


def valid_theme(code) -> str:
    return code if code in THEMES else DEFAULT_THEME


_CSS = """
<style>
:root{
  --lv-bg:__BG__; --lv-surface:__SURFACE__; --lv-surface-2:__SURFACE_2__; --lv-border:__BORDER__; --lv-edge:__EDGE__;
  --lv-text:__TEXT__; --lv-muted:__MUTED__; --lv-accent:__ACCENT__; --lv-on-accent:__ON_ACCENT__; --lv-red:__RED__;
  --lv-hover:__HOVER__; --lv-input:__INPUT__; --lv-pop:__POP__; --lv-shade:__SHADE__; --lv-pill:__PILL_BG__;
  --lv-glass: blur(22px) saturate(150%);
  color-scheme: __SCHEME__;
}
html, body, [class*="st-"], button, input, textarea, select { -webkit-font-smoothing: antialiased; }

/* ---------- liquid glass backdrop ---------- */
[data-testid="stApp"]{
  color: var(--lv-text);
  background:
    radial-gradient(circle at 12% 14%, __BG3__ 0, transparent 46%),
    radial-gradient(circle at 90% 8%, __GLOW__ 0, transparent 38%),
    radial-gradient(circle at 55% 100%, __BG2__ 0, transparent 55%),
    __BG__ !important;
  background-attachment: fixed !important;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stBottom"], [data-testid="stBottomBlockContainer"]{ background: transparent !important; }
.stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"]{ color: var(--lv-text); }
[data-testid="stCaptionContainer"], .stApp small{ color: var(--lv-muted) !important; }
.stApp a{ color: var(--lv-accent); }

/* ---------- chrome ---------- */
[data-testid="stDecoration"]{ display:none; }
[data-testid="stHeader"]{ background: transparent !important; }
[data-testid="stMainBlockContainer"], .block-container{ max-width: 1320px; padding-top: 2.6rem; padding-bottom: 4rem; }
h1{ font-weight: 650 !important; letter-spacing: -0.025em; font-size: 2rem !important; }
h2, h3{ font-weight: 600 !important; letter-spacing: -0.015em; }
hr{ border-color: var(--lv-border) !important; }

/* ---------- sidebar (glass) ---------- */
[data-testid="stSidebar"]{ background: var(--lv-surface) !important; backdrop-filter: var(--lv-glass); -webkit-backdrop-filter: var(--lv-glass);
  border-right: 1px solid var(--lv-edge); }
[data-testid="stSidebar"] > div{ background: transparent !important; }
[data-testid="stSidebarNavSeparator"]{ display:none; }
[data-testid="stNavSectionHeader"], [data-testid="stSidebarNavItems"] header{
  font-size: .68rem !important; letter-spacing: .09em; text-transform: uppercase; color: var(--lv-muted) !important;
  font-weight: 600 !important; margin-top: .9rem !important; }
[data-testid="stSidebarNavLink"]{ padding: .2rem .65rem !important; margin: 1px 0 !important; border-radius: 10px !important;
  transition: background-color .12s ease; }
/* Bug fix: Streamlit renders the label as display:table-cell + overflow:hidden inside a flex row. WebKit (Safari,
   macOS webviews) collapses it to zero width on hover repaints, so the label of the active item vanished. */
[data-testid="stSidebarNavLink"] > span:last-child{
  display:block !important; flex: 1 1 auto; min-width: 0; color: var(--lv-muted) !important; font-weight: 500; }
[data-testid="stSidebarNavLink"]:hover{ background: var(--lv-hover) !important; }
[data-testid="stSidebarNavLink"]:hover > span:last-child{ color: var(--lv-text) !important; }
[data-testid="stSidebarNavLink"][aria-current="page"]{ background: var(--lv-surface-2) !important; box-shadow: inset 0 0 0 1px var(--lv-edge); }
[data-testid="stSidebarNavLink"][aria-current="page"] > span:last-child{ color: var(--lv-text) !important; font-weight: 600; }
[data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"]{ color: var(--lv-accent) !important; }
[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"]{ color: var(--lv-muted); }

.lv-user{ display:flex; align-items:center; gap:.65rem; padding:.55rem .6rem; border:1px solid var(--lv-edge);
  border-radius:14px; background: var(--lv-surface-2); margin-bottom:.4rem; }
.lv-avatar{ width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg,#94dcd2,#367074); color:#0c1410; font-weight:700; font-size:.8rem; flex-shrink:0; }
.lv-user-meta{ min-width:0; line-height:1.25; }
.lv-user-email{ font-size:.82rem; font-weight:600; color:var(--lv-text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.lv-user-plan{ font-size:.72rem; color:var(--lv-muted); }

/* ---------- glass surfaces ---------- */
.lv-card, .lv-risk, [data-testid="stMetric"], [data-testid="stExpander"] details,
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"][class*="st-key-"]),
[data-testid="stForm"]{
  background: var(--lv-surface) !important; border: 1px solid var(--lv-edge) !important;
  backdrop-filter: var(--lv-glass); -webkit-backdrop-filter: var(--lv-glass);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 8px 28px var(--lv-shade); }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]){ border-radius: 16px; }
[data-testid="stForm"]{ border-radius: 14px !important; box-shadow: none !important; background: transparent !important;
  backdrop-filter: none; -webkit-backdrop-filter: none; }
[data-testid="stExpander"] details{ border-radius: 14px !important; }
[data-testid="stExpander"] summary{ font-weight: 500; }
[data-testid="stMetric"]{ border-radius:16px; padding: 1rem 1.1rem; }
[data-testid="stMetricLabel"] p{ color: var(--lv-muted) !important; font-size:.78rem !important; text-transform: uppercase; letter-spacing:.06em; }
[data-testid="stMetricValue"]{ font-weight: 650; letter-spacing:-.02em; color: var(--lv-text); }
[data-testid="stAlert"]{ border-radius: 14px; backdrop-filter: var(--lv-glass); -webkit-backdrop-filter: var(--lv-glass); }

/* ---------- controls ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, [data-testid="stPopover"] button{
  border-radius: 12px !important; font-weight: 500 !important; transition: all .12s ease;
  background: var(--lv-surface-2); color: var(--lv-text); border: 1px solid var(--lv-edge); }
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover{ background: var(--lv-hover); border-color: var(--lv-accent); color: var(--lv-text); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"]{
  background: var(--lv-accent) !important; color: var(--lv-on-accent) !important; font-weight:600 !important; border-color: transparent !important; }
.stButton > button[kind="primary"]:hover{ filter: brightness(1.08); }
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
[data-testid="stChatInput"], [data-testid="stFileUploaderDropzone"]{
  background: var(--lv-input) !important; border-color: var(--lv-edge) !important; border-radius: 12px !important; color: var(--lv-text); }
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea, [data-baseweb="select"] input, [data-testid="stChatInput"] textarea{
  color: var(--lv-text) !important; -webkit-text-fill-color: var(--lv-text) !important; background: transparent !important; }
[data-baseweb="select"] span, [data-baseweb="select"] div{ color: var(--lv-text); }
[data-baseweb="popover"] > div, [data-baseweb="menu"], [role="listbox"]{
  background: var(--lv-pop) !important; color: var(--lv-text) !important; border: 1px solid var(--lv-edge); border-radius: 12px; }
[data-baseweb="popover"] li, [role="option"]{ color: var(--lv-text) !important; }
[role="option"]:hover, [data-baseweb="popover"] li:hover{ background: var(--lv-hover) !important; }
[data-testid="stTabs"] [role="tablist"]{ gap: 1.4rem; border-bottom: 1px solid var(--lv-border); }
[data-testid="stTabs"] button[role="tab"]{ padding: .55rem 0 !important; }
[data-testid="stTabs"] button[role="tab"] p{ font-weight: 500; font-size: .92rem; }
[data-testid="stTabs"] button[role="tab"][aria-selected="false"] p{ color: var(--lv-muted); }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p{ color: var(--lv-text); }
[data-testid="stTabs"] [data-baseweb="tab-highlight"]{ background-color: var(--lv-accent) !important; }
[data-testid="stChatMessage"]{ background: transparent; }
[data-testid="stChatInput"] textarea{ font-size: .95rem; }
[data-testid="stCode"], pre, code{ background: var(--lv-input) !important; color: var(--lv-text) !important; border-radius: 10px; }
[data-testid="stToast"], [data-testid="stTooltipContent"]{ background: var(--lv-pop) !important; color: var(--lv-text) !important; border: 1px solid var(--lv-edge); }

/* ---------- page header ---------- */
.lv-head{ margin: 0 0 1.4rem 0; }
.lv-eyebrow{ color: var(--lv-accent); font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; font-weight:600; margin-bottom:.35rem; }
.lv-title{ font-size: 2rem; font-weight: 650; letter-spacing: -.025em; line-height:1.15; color: var(--lv-text); margin:0; }
.lv-sub{ color: var(--lv-muted); font-size: .95rem; margin-top: .4rem; }

/* ---------- small building blocks ---------- */
.lv-card{ border-radius:16px; padding:1rem 1.1rem; }
.lv-stat-label{ color:var(--lv-muted); font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; font-weight:600; }
.lv-stat-value{ font-size:1.65rem; font-weight:650; letter-spacing:-.02em; margin-top:.2rem; color:var(--lv-text); }
.lv-stat-note{ color:var(--lv-muted); font-size:.8rem; margin-top:.15rem; }
.lv-bar{ height:6px; border-radius:6px; background: var(--lv-surface-2); margin-top:.6rem; overflow:hidden; }
.lv-bar > i{ display:block; height:100%; background: linear-gradient(90deg,#94dcd2,var(--lv-accent)); border-radius:6px; }
.lv-section{ font-size:.78rem; letter-spacing:.08em; text-transform:uppercase; color:var(--lv-muted); font-weight:600; margin: 1.6rem 0 .6rem; }
.lv-list{ display:flex; flex-direction:column; }
.lv-item{ display:flex; gap:.75rem; align-items:flex-start; padding:.6rem 0; border-top:1px solid var(--lv-border); }
.lv-item:first-child{ border-top:none; }
.lv-item-dot{ width:8px; height:8px; border-radius:50%; margin-top:.45rem; flex-shrink:0; }
.lv-item-main{ flex:1; min-width:0; }
.lv-item-title{ font-size:.92rem; color:var(--lv-text); font-weight:500; }
.lv-item-sub{ font-size:.78rem; color:var(--lv-muted); margin-top:.1rem; }
.lv-item-side{ font-size:.78rem; color:var(--lv-muted); white-space:nowrap; }
.lv-row-t{ font-size:.92rem; font-weight:500; color: var(--lv-text); }
.lv-row-d{ font-size:.82rem; color: var(--lv-muted); margin-top:.15rem; line-height:1.45; }
.lv-empty{ color: var(--lv-muted); font-size:.88rem; padding:.4rem 0; }
.lv-pill{ display:inline-block; font-size:.7rem; font-weight:600; padding:.12rem .5rem; border-radius:999px;
  background: var(--lv-pill); color: var(--lv-accent); letter-spacing:.02em; }
.lv-pill.red{ background: color-mix(in srgb, var(--lv-red) 16%, transparent); color: var(--lv-red); }
.lv-pill.grey{ background: var(--lv-surface-2); color: var(--lv-muted); }
.lv-pill.amber{ background: color-mix(in srgb, __AMBER__ 16%, transparent); color: __AMBER__; }
.lv-pill.green{ background: color-mix(in srgb, __GREEN__ 16%, transparent); color: __GREEN__; }

/* ---------- case analysis: timeline and risk register ---------- */
.lv-tl{ position:relative; margin:.4rem 0 1rem .35rem; padding-left:1.4rem; border-left:2px solid var(--lv-border); }
.lv-tl-item{ position:relative; padding:.15rem 0 1.05rem; }
.lv-tl-item::before{ content:""; position:absolute; left:calc(-1.4rem - 6px); top:.42rem; width:10px; height:10px;
  border-radius:50%; background: var(--lv-muted); box-shadow: 0 0 0 3px var(--lv-bg); }
.lv-tl-item.legal::before{ background: var(--lv-accent); }
.lv-tl-item.deadline::before{ background: var(--lv-red); }
.lv-tl-date{ font-size:.74rem; letter-spacing:.06em; text-transform:uppercase; color:var(--lv-muted); font-weight:600; }
.lv-tl-ev{ font-size:.95rem; color:var(--lv-text); font-weight:500; margin-top:.1rem; line-height:1.4; }
.lv-tl-sig{ font-size:.83rem; color:var(--lv-muted); margin-top:.2rem; line-height:1.45; }
.lv-tl-src{ font-size:.72rem; color:var(--lv-muted); margin-top:.25rem; opacity:.8; }
.lv-risk{ border-left:3px solid var(--lv-muted) !important; border-radius:14px; padding:.85rem 1rem; margin-bottom:.7rem; }
.lv-risk.high{ border-left-color: var(--lv-red) !important; } .lv-risk.medium{ border-left-color: __AMBER__ !important; } .lv-risk.low{ border-left-color: __GREEN__ !important; }
.lv-risk-h{ display:flex; gap:.5rem; align-items:center; flex-wrap:wrap; }
.lv-risk-t{ font-weight:600; font-size:.95rem; color:var(--lv-text); margin-right:auto; }
.lv-risk-d{ font-size:.87rem; color:var(--lv-text); margin-top:.45rem; line-height:1.5; }
.lv-risk-m{ font-size:.83rem; color:var(--lv-muted); margin-top:.35rem; line-height:1.45; }
.lv-risk-m b{ color: var(--lv-text); font-weight:600; }
.lv-matrix{ display:grid; grid-template-columns: auto repeat(3, 1fr); gap:4px; font-size:.75rem; max-width:360px; }
.lv-matrix div{ padding:.45rem .3rem; text-align:center; border-radius:6px; color:var(--lv-muted); }
.lv-matrix .cell{ font-weight:700; font-size:.95rem; color:var(--lv-text); }
</style>
"""


def _css(theme: str) -> str:
    out = _CSS
    for k, v in THEMES[valid_theme(theme)].items():
        out = out.replace(f"__{k}__", v)
    return out


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def inject_css(theme: str | None = None):
    """Inject the stylesheet for `theme` (default: the session's theme, else dark)."""
    st.markdown(_css(theme or st.session_state.get("theme", DEFAULT_THEME)), unsafe_allow_html=True)


def html_block(markup: str):
    """Render trusted markup. Collapses indentation so Markdown never turns it into a code block."""
    st.markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def job_label(j: dict) -> str:
    """A background job's name in the session language (jobs carry a template + name for the dynamic ones)."""
    meta = j.get("meta") or {}
    return t(meta["tpl"], name=meta.get("name", "")) if "tpl" in meta else t(j["label"])


def page_header(title: str, subtitle: str = "", eyebrow: str = ""):
    title, subtitle, eyebrow = t(title), t(subtitle) if subtitle else "", t(eyebrow) if eyebrow else ""
    html_block(f"""<div class="lv-head">
        {f'<div class="lv-eyebrow">{esc(eyebrow)}</div>' if eyebrow else ''}
        <div class="lv-title">{esc(title)}</div>
        {f'<div class="lv-sub">{esc(subtitle)}</div>' if subtitle else ''}
    </div>""")


def section(label: str):
    label = t(label)
    html_block(f'<div class="lv-section">{esc(label)}</div>')


def stat(label: str, value: str, note: str = "", progress: float | None = None) -> str:
    bar = f'<div class="lv-bar"><i style="width:{max(0, min(1, progress)) * 100:.0f}%"></i></div>' if progress is not None else ""
    label, note = t(label), (t(note) if note else "")
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
