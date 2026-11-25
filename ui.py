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
                 PILL_BG="rgba(91,197,207,0.16)",
                 LINE="rgba(255,255,255,.065)", LINE2="rgba(255,255,255,.025)", WEEKEND="rgba(0,0,0,.14)",
                 EV_TEXT="#F2F4F8", EV_RING="rgba(14,17,22,.9)", SEL="rgba(255,255,255,.07)", DIM="rgba(138,147,165,.45)"),
    "light": dict(BG="#e9faf7", BG2="#94dcd2", BG3="#bff0e9", GLOW="#5bc5cf",
                  SURFACE="rgba(255,255,255,0.55)", SURFACE_2="rgba(255,255,255,0.78)",
                  BORDER="rgba(31,47,37,0.12)", EDGE="rgba(255,255,255,0.95)",
                  TEXT="#1f2f25", MUTED="rgba(31,47,37,0.64)", ACCENT="#306761", ON_ACCENT="#ffffff",
                  HOVER="rgba(48,103,97,0.09)", INPUT="rgba(255,255,255,0.72)", POP="#f4fffd",
                  SHADE="rgba(31,47,37,0.14)", SCHEME="light", RED="#C2362E", AMBER="#B4690E", GREEN="#1C7A4B",
                  PILL_BG="rgba(48,103,97,0.13)",
                  LINE="rgba(31,47,37,.10)", LINE2="rgba(31,47,37,.045)", WEEKEND="rgba(31,47,37,.055)",
                  EV_TEXT="#12302c", EV_RING="rgba(255,255,255,.85)", SEL="rgba(48,103,97,.13)", DIM="rgba(31,47,37,.34)"),
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
  --lv-line:__LINE__; --lv-line2:__LINE2__; --lv-weekend:__WEEKEND__; --lv-ev-text:__EV_TEXT__; --lv-ev-ring:__EV_RING__; --lv-sel:__SEL__; --lv-dim:__DIM__;
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
  font-size: .8rem !important; color: var(--lv-muted) !important;
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

/* ---------- hand-drawn side list (views/account_menu.nav) ---------- */
[data-testid="stSidebarUserContent"]{ padding-top: .4rem; }
.lv-navsec{ font-size:.8rem; color:var(--lv-muted); font-weight:600;
  margin:1.1rem 0 .3rem .65rem; }
[class*="st-key-nav_"]{ margin:0 !important; }
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]{ gap:2px; }
[data-testid="stSidebarUserContent"] .st-key-acct{ margin-bottom:.4rem; }
[class*="st-key-nav_"] a{ padding:.38rem .65rem !important; border-radius:10px !important; transition: background-color .12s ease; }
[class*="st-key-nav_"] a:hover{ background: var(--lv-hover) !important; }
[class*="st-key-nav_"] a p, [class*="st-key-nav_"] a span{ color: var(--lv-muted) !important; font-weight:500; font-size:.9rem; }
[class*="st-key-nav_"] a:hover p{ color: var(--lv-text) !important; }
[class*="st-key-nav_"][class*="_on"] a{ background: var(--lv-surface-2) !important; box-shadow: inset 0 0 0 1px var(--lv-edge); }
[class*="st-key-nav_"][class*="_on"] a p{ color: var(--lv-text) !important; font-weight:600; }
[class*="st-key-nav_"][class*="_on"] a [data-testid="stIconMaterial"]{ color: var(--lv-accent) !important; }

/* ---------- account card + flyout (views/account_menu) ---------- */
.st-key-acct [data-testid="stPopoverButton"]{ position:relative; justify-content:flex-start !important; text-align:left;
  min-height:3.6rem; padding:.5rem 2rem .5rem 3.5rem !important; border-radius:14px !important;
  background: var(--lv-surface-2) !important; border:1px solid var(--lv-edge) !important; }
.st-key-acct [data-testid="stPopoverButton"]:hover{ border-color: var(--lv-accent) !important; }
.st-key-acct [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"]{ min-width:0; overflow:hidden; }
.st-key-acct [data-testid="stPopoverButton"] p{ margin:0; font-size:.78rem; line-height:1.3; color: var(--lv-muted) !important;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.st-key-acct [data-testid="stPopoverButton"] p::first-line{ font-weight:600; font-size:.9rem; color: var(--lv-text); }
.st-key-acct [data-testid="stPopoverButton"] > div:last-child{ position:absolute; right:.7rem; }
.st-key-acct [data-testid="stPopoverButton"]::before{ position:absolute; left:.65rem; top:50%; transform:translateY(-50%);
  width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(135deg,#94dcd2,#367074); color:#0c1410; font-weight:700; font-size:.78rem; }
.st-key-acct [data-testid="stPopoverButton"]::after{ position:absolute; top:-6px; right:-5px; min-width:18px; height:18px;
  padding:0 5px; border-radius:9px; background: var(--lv-red); color:#fff; font-size:.66rem; font-weight:700;
  display:flex; align-items:center; justify-content:center; box-sizing:border-box; }
[data-testid="stPopoverBody"]{ background: var(--lv-pop) !important; border:none !important;
  border-radius:16px !important; box-shadow: 0 18px 50px var(--lv-shade) !important; color: var(--lv-text); }
[data-testid="stPopoverBody"]:has(.lv-pm-head){ width:320px !important; min-width:320px; max-height:82vh; overflow-y:auto;
  padding:.9rem .7rem .6rem !important; }
[data-testid="stPopoverBody"]:has(.lv-pm-head) [data-testid="stVerticalBlock"]{ gap:1px; }
[data-testid="stPopoverBody"]:has(.lv-pm-head) [data-testid="stHorizontalBlock"]{ gap:.4rem; }
[data-testid="stPopoverBody"]:has(.lv-pm-head) .stButton button,
[data-testid="stPopoverBody"]:has(.lv-pm-head) [data-testid="stPageLink-NavLink"]{
  display:flex; justify-content:flex-start !important; gap:.6rem; width:100%; min-height:2.3rem; padding:.35rem .6rem !important;
  background:transparent !important; border:none !important; box-shadow:none !important; border-radius:9px !important; }
[data-testid="stPopoverBody"]:has(.lv-pm-head) .stButton button:hover,
[data-testid="stPopoverBody"]:has(.lv-pm-head) [data-testid="stPageLink-NavLink"]:hover{ background: var(--lv-hover) !important; }
[data-testid="stPopoverBody"]:has(.lv-pm-head) .stButton button p,
[data-testid="stPopoverBody"]:has(.lv-pm-head) [data-testid="stPageLink-NavLink"] p{ color: var(--lv-text) !important;
  font-size:.88rem !important; font-weight:500; }
[data-testid="stPopoverBody"]:has(.lv-pm-head) [data-testid="stIconMaterial"]{ color: var(--lv-muted); font-size:1.15rem; }
.st-key-pm_msg_clear button{ justify-content:center !important; }
.st-key-pm_dur{ padding:0 .2rem .2rem; }
.st-key-pm_msg{ padding:0 .2rem; }
/* Streamlit pulls every markdown block up by 1rem; our menu labels and separators need their real height */
[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebarUserContent"] [data-testid="stMarkdownContainer"]:has(.lv-navsec){ margin-bottom:0 !important; }
.lv-pm-head{ display:flex; gap:.8rem; align-items:center; padding:0 .45rem .55rem; }
.lv-pm-av{ position:relative; width:48px; height:48px; flex-shrink:0; border-radius:50%; display:flex; align-items:center;
  justify-content:center; background:linear-gradient(135deg,#94dcd2,#367074); color:#0c1410; font-weight:700; font-size:1rem; }
.lv-pm-av::after{ content:""; position:absolute; right:-1px; bottom:-1px; width:14px; height:14px; border-radius:50%;
  box-shadow:0 0 0 3px var(--lv-pop); }
.lv-pm-who{ min-width:0; line-height:1.3; }
.lv-pm-name{ font-weight:650; font-size:1rem; color:var(--lv-text); }
.lv-pm-mail{ font-size:.8rem; color:var(--lv-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.lv-pm-plan{ font-size:.74rem; color:var(--lv-accent); font-weight:600; margin-top:.15rem; }
.lv-pm-label{ font-size:.78rem; color:var(--lv-muted); font-weight:600;
  margin:0; padding:.8rem .6rem .35rem; }
.st-key-pm_st_busy [data-testid="stIconMaterial"]{ font-variation-settings:'FILL' 1; }
.st-key-pm_msg [data-baseweb="input"]{ min-height:2.3rem; }
.lv-pm-sep{ height:1px; background: var(--lv-border); margin:.55rem .3rem; }

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
[data-testid="stMetricLabel"] p{ color: var(--lv-muted) !important; font-size:.86rem !important; }
[data-testid="stMetricValue"]{ font-weight: 650; letter-spacing:-.02em; color: var(--lv-text); }
[data-testid="stAlert"]{ border-radius: 14px; backdrop-filter: var(--lv-glass); -webkit-backdrop-filter: var(--lv-glass); }

/* ---------- controls ---------- */
.stButton button, .stDownloadButton button, .stFormSubmitButton button, [data-testid="stPopover"] button{
  border-radius: 12px !important; font-weight: 500 !important; transition: all .12s ease;
  background: var(--lv-surface-2); color: var(--lv-text); border: 1px solid var(--lv-edge); }
.stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover{ background: var(--lv-hover); border-color: var(--lv-accent); color: var(--lv-text); }
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primaryFormSubmit"]{
  background: var(--lv-accent) !important; color: var(--lv-on-accent) !important; font-weight:600 !important; border-color: transparent !important; }
.stButton button[kind="primary"]:hover{ filter: brightness(1.08); }
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

/* segmented controls and pills (Streamlit paints these with its dark base theme, so restyle them) */
[data-testid="stButtonGroup"] button{ background: var(--lv-input) !important; color: var(--lv-muted) !important;
  border: 1px solid var(--lv-edge) !important; box-shadow:none !important; }
[data-testid="stButtonGroup"] button p, [data-testid="stButtonGroup"] button span{ color: inherit !important; }
[data-testid="stButtonGroup"] button:hover{ background: var(--lv-hover) !important; color: var(--lv-text) !important; }
[data-testid="stButtonGroup"] button[data-testid$="Active"], [data-testid="stButtonGroup"] button[aria-checked="true"],
[data-testid="stButtonGroup"] button[aria-pressed="true"]{
  background: var(--lv-pill) !important; color: var(--lv-accent) !important; border-color: var(--lv-accent) !important; font-weight:600; }
[data-baseweb="checkbox"] > div:first-child, [data-baseweb="radio"] > div:first-child{ border-color: var(--lv-edge) !important; }
[data-testid="stAlert"]{ color: var(--lv-text); }
[data-testid="stAlert"] p{ color: var(--lv-text) !important; }
[data-testid="stFileUploaderDropzone"] *, [data-testid="stAudioInput"] *{ color: var(--lv-text); }
[data-testid="stAudioInput"], [data-testid="stDataFrame"]{ background: var(--lv-input); border-radius:12px; }
[data-testid="stProgress"] > div > div{ background: var(--lv-surface-2) !important; }
[data-testid="stChatMessage"] p{ color: var(--lv-text); }

/* primary buttons: the label is a <p>, which the global text colour would otherwise repaint */
.stButton button[kind="primary"] p, .stButton button[kind="primary"] [data-testid="stIconMaterial"],
.stFormSubmitButton button[kind="primaryFormSubmit"] p, .stDownloadButton button[kind="primary"] p{ color: var(--lv-on-accent) !important; }

/* chat input dock (the strip under the chat stays transparent in both themes) */
[data-testid="stBottom"], [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"]{ background: transparent !important; }
[data-testid="stChatInput"]{ border:1px solid var(--lv-edge) !important; border-radius:16px !important; box-shadow: 0 8px 28px var(--lv-shade); }
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"]{ background: transparent !important; border:none !important; }
[data-testid="stChatInput"] button{ background: transparent !important; color: var(--lv-accent) !important; }
[data-testid="stChatInputSubmitButton"] svg{ fill: var(--lv-accent); color: var(--lv-accent); }

/* themed tables (ui.table) and the Files list */
.lv-table{ border:1px solid var(--lv-edge); border-radius:14px; overflow:hidden; background: var(--lv-surface); }
.lv-table.scroll{ max-height:460px; overflow-y:auto; }
.lv-table table{ width:100%; border-collapse:collapse; font-size:.86rem; }
.lv-table th{ text-align:left; font-size:.8rem; color: var(--lv-muted);
  font-weight:600; padding:.65rem .9rem; border-bottom:1px solid var(--lv-border); background: var(--lv-surface-2);
  position:sticky; top:0; }
.lv-table td{ padding:.6rem .9rem; border-bottom:1px solid var(--lv-border); color: var(--lv-text); }
.lv-table tr:last-child td{ border-bottom:none; }
.lv-table tbody tr:hover td{ background: var(--lv-hover); }
.st-key-ftable{ border:1px solid var(--lv-edge); border-radius:14px; background: var(--lv-surface); padding:.2rem .9rem;
  gap:0 !important; backdrop-filter: var(--lv-glass); -webkit-backdrop-filter: var(--lv-glass); }
.st-key-ftable > [data-testid="stHorizontalBlock"]{ padding:.55rem 0 .45rem; border-bottom:1px solid var(--lv-border); }
.st-key-ftable [data-testid="stMarkdownContainer"]{ margin-bottom:0 !important; }
.st-key-ftable [data-testid="stHorizontalBlock"]{ align-items:center; }
.lv-th{ white-space:nowrap; font-size:.8rem; color: var(--lv-muted); font-weight:600; }
[class*="st-key-frow_"]{ padding:.45rem .5rem; margin:0 -.5rem; border-bottom:1px solid var(--lv-border); border-radius:10px; }
[class*="st-key-frow_"]:last-child{ border-bottom:none; }
[class*="st-key-frow_"]:hover{ background: var(--lv-hover); }
[class*="st-key-frow_"][class*="_on"]{ background: var(--lv-pill); }
.lv-td-main{ font-size:.9rem; font-weight:500; color: var(--lv-text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.lv-td{ font-size:.86rem; color: var(--lv-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
[class*="st-key-frow_"] .stButton button{ min-height:2rem; padding:.1rem .6rem; white-space:nowrap; }
[class*="st-key-frow_"] .stButton button p{ white-space:nowrap; }

/* ---------- page header ---------- */
.lv-head{ margin: 0 0 1.4rem 0; }
.lv-eyebrow{ color: var(--lv-accent); font-size:.72rem; font-weight:600; margin-bottom:.35rem; }
.lv-title{ font-size: 2rem; font-weight: 650; letter-spacing: -.025em; line-height:1.15; color: var(--lv-text); margin:0; }
.lv-sub{ color: var(--lv-muted); font-size: .95rem; margin-top: .4rem; }

/* ---------- small building blocks ---------- */
.lv-card{ border-radius:16px; padding:1rem 1.1rem; }
.lv-card.lv-stat{ min-height:8.1rem; box-sizing:border-box; display:flex; flex-direction:column; justify-content:flex-start; }
.lv-news{ display:flex; gap:.9rem; align-items:flex-start; }
.lv-news-body{ flex:1; min-width:0; }
.lv-thumb{ position:relative; width:112px; height:84px; flex-shrink:0; border-radius:12px; overflow:hidden;
  background: linear-gradient(135deg, var(--lv-pill), var(--lv-surface-2)); display:flex; align-items:center; justify-content:center;
  color: var(--lv-accent); border:1px solid var(--lv-border); }
.lv-thumb-ico{ font-size:30px; opacity:.75; }
.lv-thumb img{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }
.lv-bar.empty{ visibility:hidden; }
.lv-avatar.big{ width:76px; height:76px; font-size:1.6rem; }
.lv-profile{ display:flex; gap:1.3rem; align-items:center; padding:1.3rem 1.5rem; }
.lv-profile-name{ font-size:1.5rem; font-weight:650; letter-spacing:-.02em; color:var(--lv-text); }
.lv-profile-msg{ font-size:.9rem; color:var(--lv-text); margin-top:.35rem; font-style:italic; }
.lv-profile-tags{ display:flex; gap:.4rem; margin-top:.55rem; flex-wrap:wrap; }
.st-key-dash_cal [data-testid="stHorizontalBlock"]{ align-items: stretch; }
.st-key-dash_cal [data-testid="stAlert"]{ margin:0; min-height:3.4rem; }
.st-key-dash_cal .stButton button{ min-height:3.4rem; height:100%; }
.lv-stat-label{ color:var(--lv-muted); font-size:.84rem; font-weight:600; }
.lv-stat-value{ font-size:1.65rem; font-weight:650; letter-spacing:-.02em; margin-top:.2rem; color:var(--lv-text); }
.lv-stat-note{ color:var(--lv-muted); font-size:.8rem; margin-top:.15rem; }
.lv-bar{ height:6px; border-radius:6px; background: var(--lv-surface-2); margin-top:.6rem; overflow:hidden; }
.lv-bar > i{ display:block; height:100%; background: linear-gradient(90deg,#94dcd2,var(--lv-accent)); border-radius:6px; }
.lv-section{ font-family:var(--lv-serif); font-size:1.2rem; color:var(--lv-text); font-weight:500; margin: 2rem 0 .7rem; }
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
  background: var(--lv-pill); color: var(--lv-accent); }
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
.lv-tl-date{ font-size:.8rem; color:var(--lv-muted); font-weight:600; }
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
/* ---------- type: a serif for the things people read first, a quiet grotesque for everything else ---------- */
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=Instrument+Sans:wght@400;500;600;700&display=swap');
:root{ --lv-serif: 'Newsreader', 'Iowan Old Style', Georgia, serif; --lv-sans: 'Instrument Sans', 'Inter', system-ui, sans-serif; }
html, body, [data-testid="stApp"], .stApp button, input, textarea, select{ font-family: var(--lv-sans); }
h1, .lv-title, .lv-calt, .lv-set-h, .lv-profile-name{ font-family: var(--lv-serif) !important; font-weight: 500 !important; letter-spacing:-.015em; }
h1, .lv-title{ font-size: 2.4rem !important; line-height:1.1; }
.lv-head{ margin-bottom: 1.8rem; }
.lv-sub{ font-size:1rem; max-width:62ch; }
.lv-stat-value{ font-family: var(--lv-serif); font-size:clamp(1.6rem, 2.3vw, 2.2rem); white-space:nowrap; font-weight:500; line-height:1.1; font-variant-numeric: lining-nums tabular-nums; }
.lv-card.lv-stat{ padding:1.1rem 1.2rem; min-height:9.6rem; }
.lv-item{ padding:.7rem 0; }
.lv-item-title{ line-height:1.35; }
.lv-empty{ padding:.6rem 0; }
.lv-card .lv-empty{ font-size:.92rem; }
[data-testid="stSidebarNavLink"] > span:last-child{ font-size:.93rem; }

.st-key-settings_nav label p{ white-space:nowrap; }
[data-testid="stPageLink-NavLink"]{ border-radius:12px; padding:.45rem .8rem; }
[data-testid="stPageLink-NavLink"]:hover{ background: var(--lv-hover); }

[data-testid="stFileUploaderDropzone"] button{ background: var(--lv-surface-2) !important; border:1px solid var(--lv-edge) !important; border-radius:12px !important; }
[data-testid="stFileUploaderDropzone"] button:hover{ border-color: var(--lv-accent) !important; }
[data-testid="stFileUploaderDropzone"] button *{ color: var(--lv-text) !important; }

/* ---------- keyboard focus + reduced motion ---------- */
:is(button, a, input, textarea, select, [role="tab"], [role="option"]):focus-visible,
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within{
  outline: 2px solid var(--lv-accent) !important; outline-offset: 2px; }
::selection{ background: var(--lv-pill); }
@media (max-width: 760px){
  h1, .lv-title{ font-size: 1.9rem !important; }
  .lv-stat-value{ font-size:1.8rem; }
  [data-testid="stMainBlockContainer"], .block-container{ padding-top: 3.2rem; padding-left:1rem; padding-right:1rem; }
  .lv-card.lv-stat{ min-height:0; margin-bottom:.6rem; }
  .lv-bar.empty{ display:none; }
  .lv-profile{ flex-direction:column; align-items:flex-start; }
}
@media (prefers-reduced-motion: reduce){ *{ transition:none !important; animation:none !important; scroll-behavior:auto !important; } }
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
        <div class="lv-title">{esc(title)}</div>
        {f'<div class="lv-sub">{esc(subtitle)}</div>' if subtitle else ''}
    </div>""")


def section(label: str):
    label = t(label)
    html_block(f'<div class="lv-section">{esc(label)}</div>')


def stat(label: str, value: str, note: str = "", progress: float | None = None) -> str:
    bar = (f'<div class="lv-bar"><i style="width:{max(0, min(1, progress)) * 100:.0f}%"></i></div>'
           if progress is not None else '<div class="lv-bar empty"></div>')
    label, note = t(label), (t(note) if note else "")
    return (f'<div class="lv-card lv-stat"><div class="lv-stat-label">{esc(label)}</div>'
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



def table(headers, rows, scroll: bool = False):
    """A themed HTML table (st.dataframe draws on a canvas and ignores the light theme). Cells are escaped."""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    html_block(f'<div class="lv-table{" scroll" if scroll else ""}"><table><thead><tr>{head}</tr></thead>'
               f'<tbody>{body}</tbody></table></div>')
