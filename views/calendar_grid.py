"""HTML rendering for the calendar (Day / Week time grid, Month grid, mini month), modelled on Apple Calendar.

Pure functions: they take plain event dicts and return markup, so they're easy to test. Every piece of user text
is escaped with ui.esc before it is placed in HTML.

Event dict: {start, end, title, kind, tentative, sub}
kind: event | meeting | deadline | task | busy
"""
from __future__ import annotations
import calendar as _calendar
import datetime as dt
import math
from typing import Iterable, List, Optional
import i18n
from i18n import t
from ui import esc

HOUR_PX = 52
DEFAULT_HOURS = (7, 21)
GUTTER_PX = 58

COLORS = {
    "event": "#0A84FF",     # blue: your own events
    "meeting": "#BF5AF2",   # purple: meetings with other people
    "deadline": "#FF453A",  # red: case deadlines
    "task": "#FF9F0A",      # orange: case tasks with a due date
    "busy": "#8E8E93",      # grey: someone else's busy block
}
LEGEND = [("event", "My events"), ("meeting", "Meetings"), ("deadline", "Case deadlines"), ("task", "Case tasks")]
BUSY = "Busy"  # label of someone else's busy block (see cal.py)


def _rgba(hex_color: str, a: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def _ts(d: dt.date, hour: float = 0) -> float:
    return dt.datetime.combine(d, dt.time(0)).timestamp() + hour * 3600


def _fmt_time(ts: float) -> str:
    t = dt.datetime.fromtimestamp(ts)
    return t.strftime("%H:%M")


def _compact(markup: str) -> str:
    return "".join(line.strip() for line in markup.splitlines())


CSS = _compact("""<style>
.lvc{ border:1px solid var(--lv-border); border-radius:14px; overflow:hidden; background:var(--lv-surface); }
.lvc-head, .lvc-body{ display:grid; }
.lvc-head{ border-bottom:1px solid var(--lv-border); }
.lvc-dh{ padding:10px 6px 9px; text-align:center; border-left:1px solid var(--lv-border); }
.lvc-dh:first-child{ border-left:none; }
.lvc-dow{ font-size:11px; letter-spacing:.07em; text-transform:uppercase; color:var(--lv-muted); font-weight:600; }
.lvc-dn{ display:inline-flex; align-items:center; justify-content:center; min-width:34px; height:34px; padding:0 6px;
  margin-top:3px; border-radius:17px; font-size:21px; font-weight:500; color:var(--lv-text); letter-spacing:-.02em; }
.lvc-dh.we .lvc-dn{ color:var(--lv-muted); }
.lvc-dh.today .lvc-dow{ color:#FF453A; }
.lvc-dh.today .lvc-dn{ background:#FF453A; color:#fff; font-weight:600; }
.lvc-dh.big{ text-align:left; padding:12px 16px; }
.lvc-dh.big .lvc-dn{ font-size:26px; justify-content:flex-start; padding:0; min-width:0; background:none !important; }
.lvc-dh.big.today .lvc-dn{ color:#FF453A; }
.lvc-gut{ position:relative; }
.lvc-hr{ position:absolute; right:8px; font-size:10.5px; color:var(--lv-muted); transform:translateY(-50%); font-variant-numeric:tabular-nums; }
.lvc-nowlbl{ position:absolute; right:4px; transform:translateY(-50%); font-size:10.5px; font-weight:600; color:#FF453A;
  background:var(--lv-surface); padding:0 3px; z-index:3; font-variant-numeric:tabular-nums; }
.lvc-col{ position:relative; border-left:1px solid var(--lv-border);
  background-image:repeating-linear-gradient(to bottom, rgba(255,255,255,.065) 0, rgba(255,255,255,.065) 1px, transparent 1px, transparent @H@px),
                   repeating-linear-gradient(to bottom, transparent 0, transparent @HH@px, rgba(255,255,255,.025) @HH@px, rgba(255,255,255,.025) @HH1@px, transparent @HH1@px, transparent @H@px); }
.lvc-col.we{ background-color:rgba(0,0,0,.14); }
.lvc-col.today{ background-color:rgba(255,69,58,.035); }
.lvc-ev{ position:absolute; border-radius:6px; padding:3px 6px 3px 7px; overflow:hidden; font-size:11.5px; line-height:1.28;
  border-left:3px solid; box-shadow:0 0 0 1px rgba(14,17,22,.9); }
.lvc-ev b{ display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; font-weight:600; overflow:hidden; word-break:break-word; }
.lvc-ev span{ display:block; opacity:.82; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.lvc-ev.short{ display:flex; gap:6px; align-items:center; padding-top:1px; padding-bottom:1px; }
.lvc-ev.short b{ flex:0 1 auto; display:block; white-space:nowrap; text-overflow:ellipsis; } .lvc-ev.short span{ flex:0 0 auto; }
.lvc-ev.tent{ border-left-style:dashed; }
.lvc-now{ position:absolute; left:0; right:0; height:0; border-top:2px solid #FF453A; z-index:2; }
.lvc-now:before{ content:""; position:absolute; left:-5px; top:-6px; width:10px; height:10px; border-radius:50%; background:#FF453A; }
.lvc-nowfaint{ position:absolute; left:0; right:0; height:0; border-top:1px solid rgba(255,69,58,.35); z-index:1; }

.lvm{ border:1px solid var(--lv-border); border-radius:14px; overflow:hidden; background:var(--lv-surface); }
.lvm-head, .lvm-grid{ display:grid; grid-template-columns:repeat(7, minmax(0,1fr)); }
.lvm-head div{ padding:9px 10px; text-align:right; font-size:11px; letter-spacing:.07em; text-transform:uppercase;
  color:var(--lv-muted); font-weight:600; border-bottom:1px solid var(--lv-border); }
.lvm-grid{ grid-auto-rows:minmax(116px, auto); }
.lvm-cell{ padding:5px 5px 6px; border-left:1px solid var(--lv-border); border-top:1px solid var(--lv-border); min-width:0; }
.lvm-cell:nth-child(7n+1){ border-left:none; }
.lvm-cell:nth-child(-n+7){ border-top:none; }
.lvm-cell.we{ background:rgba(0,0,0,.14); }
.lvm-cell.out .lvm-num{ color:rgba(138,147,165,.45); }
.lvm-top{ display:flex; justify-content:flex-end; margin-bottom:3px; }
.lvm-num{ display:inline-flex; align-items:center; justify-content:center; min-width:26px; height:26px; padding:0 7px;
  border-radius:13px; font-size:13px; font-weight:500; color:var(--lv-text); font-variant-numeric:tabular-nums; }
.lvm-cell.today .lvm-num{ background:#FF453A; color:#fff; font-weight:600; }
.lvm-ev{ display:flex; align-items:center; gap:5px; font-size:11.5px; line-height:1.2; padding:2px 4px; border-radius:5px;
  white-space:nowrap; overflow:hidden; margin-bottom:1px; color:var(--lv-text); }
.lvm-ev i{ width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.lvm-ev em{ font-style:normal; overflow:hidden; text-overflow:ellipsis; flex:1; min-width:0; }
.lvm-ev small{ color:var(--lv-muted); font-size:10.5px; font-variant-numeric:tabular-nums; }
.lvm-ev.fill{ font-weight:500; }
.lvm-more{ font-size:11px; color:var(--lv-muted); padding:1px 4px; font-weight:500; }

.lvmini{ user-select:none; }
.lvmini-t{ font-size:13px; font-weight:600; color:var(--lv-text); margin:2px 2px 8px; }
.lvmini-g{ display:grid; grid-template-columns:repeat(7,1fr); row-gap:2px; text-align:center; }
.lvmini-g .h{ font-size:10px; color:var(--lv-muted); font-weight:600; padding-bottom:4px; }
.lvmini-g .d{ position:relative; font-size:11.5px; height:26px; display:flex; align-items:center; justify-content:center;
  color:var(--lv-text); font-variant-numeric:tabular-nums; }
.lvmini-g .d.out{ color:rgba(138,147,165,.4); }
.lvmini-g .d.sel{ background:rgba(255,255,255,.07); }
.lvmini-g .d.sel.l{ border-top-left-radius:8px; border-bottom-left-radius:8px; }
.lvmini-g .d.sel.r{ border-top-right-radius:8px; border-bottom-right-radius:8px; }
.lvmini-g .d.today span{ background:#FF453A; color:#fff; font-weight:600; }
.lvmini-g .d span{ width:22px; height:22px; border-radius:11px; display:flex; align-items:center; justify-content:center; }
.lvmini-g .d.has:after{ content:""; position:absolute; bottom:1px; width:3px; height:3px; border-radius:50%; background:var(--lv-muted); }
.lvleg{ margin-top:18px; }
.lvleg-t{ font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--lv-muted); font-weight:600; margin:0 2px 6px; }
.lvleg-r{ display:flex; align-items:center; gap:9px; font-size:13px; color:var(--lv-text); padding:4px 2px; }
.lvleg-r i{ width:12px; height:12px; border-radius:4px; flex-shrink:0; }
</style>""".replace("@HH1@", str(HOUR_PX // 2 + 1)).replace("@HH@", str(HOUR_PX // 2)).replace("@H@", str(HOUR_PX)))


def event_style(kind: str, tentative: bool = False) -> str:
    c = COLORS.get(kind, COLORS["event"])
    if tentative:
        bg = (f"repeating-linear-gradient(135deg,{_rgba(c, .16)} 0,{_rgba(c, .16)} 6px,"
              f"{_rgba(c, .06)} 6px,{_rgba(c, .06)} 12px)")
    else:
        bg = _rgba(c, .30)
    return f"background:{bg};border-left-color:{c};color:#F2F4F8;"


# ---------- layout ----------
def layout_day(events: Iterable[dict], day: dt.date):
    """Place a day's events side by side where they overlap. Returns [(event, start, end, col, ncols)]."""
    d0, d1 = _ts(day), _ts(day + dt.timedelta(days=1))
    clipped = sorted(((e, max(e["start"], d0), min(e["end"], d1)) for e in events
                      if e["start"] < d1 and e["end"] > d0), key=lambda x: (x[1], -x[2]))
    out, cluster, col_ends, cluster_end = [], [], [], None

    def flush():
        n = len(col_ends)
        out.extend((e, s, en, c, n) for e, s, en, c in cluster)

    for e, s, en in clipped:
        en_vis = max(en, s + 1200)  # very short events still need room to be readable
        if cluster_end is not None and s >= cluster_end:
            flush()
            cluster, col_ends, cluster_end = [], [], None
        for c, end in enumerate(col_ends):
            if end <= s:
                col_ends[c] = en_vis
                break
        else:
            c = len(col_ends)
            col_ends.append(en_vis)
        cluster.append((e, s, en, c))
        cluster_end = en_vis if cluster_end is None else max(cluster_end, en_vis)
    flush()
    return out


def hour_range(events: Iterable[dict], days: List[dt.date]):
    lo, hi = DEFAULT_HOURS
    for day in days:
        d0 = _ts(day)
        for e in events:
            if e["start"] < d0 + 86400 and e["end"] > d0:
                lo = min(lo, math.floor(max(0.0, (e["start"] - d0) / 3600)))
                hi = max(hi, math.ceil(min(24.0, (e["end"] - d0) / 3600)))
    return max(0, lo), min(24, hi)


# ---------- Day / Week time grid ----------
def time_grid(days: List[dt.date], events: List[dict], now: Optional[float] = None) -> str:
    now = dt.datetime.now().timestamp() if now is None else now
    today = dt.date.fromtimestamp(now)
    lo, hi = hour_range(events, days)
    if today in days:  # keep the current-time line in view, as Apple Calendar does
        now_h = (now - _ts(today)) / 3600
        lo, hi = min(lo, math.floor(now_h)), max(hi, min(24, math.floor(now_h) + 1))
    height = (hi - lo) * HOUR_PX
    cols = f"grid-template-columns:{GUTTER_PX}px repeat({len(days)}, minmax(0,1fr));"
    single = len(days) == 1

    head = ['<div class="lvc-dh" style="border-left:none"></div>']
    for d in days:
        cls = "lvc-dh" + (" today" if d == today else "") + (" we" if d.weekday() >= 5 else "") + (" big" if single else "")
        if single:
            head.append(f'<div class="{cls}"><div class="lvc-dow">{i18n.fmt(d, "%A")}</div><div class="lvc-dn">'
                        f'{i18n.fmt(d, i18n._by_lang("%B %-d", "%-d %B"))}</div></div>')
        else:
            head.append(f'<div class="{cls}"><div class="lvc-dow">{i18n.fmt(d, "%a")}</div><div class="lvc-dn">{d.day}</div></div>')

    gut = [f'<div class="lvc-gut" style="height:{height}px">']
    for h in range(lo + 1, hi):
        gut.append(f'<div class="lvc-hr" style="top:{(h - lo) * HOUR_PX}px">{h:02d}:00</div>')
    now_in_view = today in days and lo * 3600 <= now - _ts(today) <= hi * 3600
    now_top = (now - _ts(today, lo)) / 3600 * HOUR_PX
    if now_in_view:
        gut.append(f'<div class="lvc-nowlbl" style="top:{now_top:.0f}px">{_fmt_time(now)}</div>')
    gut.append("</div>")

    body_cols = []
    for d in days:
        cls = "lvc-col" + (" today" if d == today else "") + (" we" if d.weekday() >= 5 else "")
        parts = [f'<div class="{cls}" style="height:{height}px">']
        top0 = _ts(d, lo)
        for e, s, en, c, n in layout_day(events, d):
            top = max(0.0, (s - top0) / 3600 * HOUR_PX)
            h = max(20.0, (en - s) / 3600 * HOUR_PX - 2)
            h = min(h, height - top)
            w = 100 / n
            short = h < 36
            title = esc(t(e["title"]) if e.get("kind") == "busy" else e["title"])
            when = f"{_fmt_time(e['start'])}" if e["end"] - e["start"] <= 1800 and e.get("kind") in ("deadline", "task") \
                else f"{_fmt_time(e['start'])} – {_fmt_time(e['end'])}"
            sub = f"<span>{esc(when)}</span>"
            if not short and e.get("sub") and h >= 58:
                sub += f"<span>{esc(e['sub'])}</span>"
            tip = esc(f"{e['title']} · {when}" + (f" · {e['sub']}" if e.get("sub") else "")
                      + (" · " + t("Tentative").lower() if e.get("tentative") else ""))
            parts.append(
                f'<div class="lvc-ev{" short" if short else ""}{" tent" if e.get("tentative") else ""}" title="{tip}" '
                f'style="top:{top:.1f}px;height:{h:.1f}px;left:calc({c * w:.4f}% + 2px);width:calc({w:.4f}% - 5px);'
                f'{event_style(e.get("kind", "event"), e.get("tentative", False))}"><b>{title}</b>{sub}</div>')
        if now_in_view:
            line = "lvc-now" if d == today else "lvc-nowfaint"
            parts.append(f'<div class="{line}" style="top:{now_top:.0f}px"></div>')
        parts.append("</div>")
        body_cols.append("".join(parts))

    return (f'<div class="lvc"><div class="lvc-head" style="{cols}">{"".join(head)}</div>'
            f'<div class="lvc-body" style="{cols}">{"".join(gut)}{"".join(body_cols)}</div></div>')


# ---------- Month grid ----------
def month_days(year: int, month: int) -> List[dt.date]:
    """42 days (6 weeks, Monday first) covering the month."""
    first = dt.date(year, month, 1)
    start = first - dt.timedelta(days=first.weekday())
    return [start + dt.timedelta(days=i) for i in range(42)]


def month_grid(year: int, month: int, events: List[dict], today: Optional[dt.date] = None, per_day: int = 4) -> str:
    today = today or dt.date.today()
    head = "".join(f"<div>{i18n.day_short(i)}</div>" for i in range(7))
    cells = []
    for d in month_days(year, month):
        d0, d1 = _ts(d), _ts(d + dt.timedelta(days=1))
        todays = sorted((e for e in events if e["start"] < d1 and e["end"] > d0), key=lambda e: e["start"])
        cls = "lvm-cell" + (" out" if d.month != month else "") + (" today" if d == today else "") + \
              (" we" if d.weekday() >= 5 else "")
        label = i18n.date_md(d) if d.day == 1 else str(d.day)
        rows = []
        shown = todays if len(todays) <= per_day else todays[:per_day - 1]
        for e in shown:
            c = COLORS.get(e.get("kind", "event"), COLORS["event"])
            tip = esc(f"{e['title']} · {_fmt_time(e['start'])}" + (f" · {e['sub']}" if e.get("sub") else ""))
            if e.get("kind") in ("deadline", "task"):
                rows.append(f'<div class="lvm-ev fill" title="{tip}" style="background:{_rgba(c, .22)}">'
                            f'<em>{esc(e["title"])}</em></div>')
            else:
                dot = f"background:{c}" if not e.get("tentative") else f"border:1.5px solid {c};box-sizing:border-box"
                rows.append(f'<div class="lvm-ev" title="{tip}"><i style="{dot}"></i><em>{esc(e["title"])}</em>'
                            f'<small>{_fmt_time(max(e["start"], d0))}</small></div>')
        if len(todays) > len(shown):
            rows.append(f'<div class="lvm-more">{esc(t("{n} more", n=len(todays) - len(shown)))}</div>')
        cells.append(f'<div class="{cls}"><div class="lvm-top"><span class="lvm-num">{esc(label)}</span></div>'
                     f'{"".join(rows)}</div>')
    return f'<div class="lvm"><div class="lvm-head">{head}</div><div class="lvm-grid">{"".join(cells)}</div></div>'


# ---------- sidebar: mini month + legend ----------
def mini_month(year: int, month: int, sel_start: dt.date, sel_end: dt.date, busy_days=(), today=None) -> str:
    """sel_end is exclusive."""
    today = today or dt.date.today()
    busy_days = set(busy_days)
    cells = ["".join(f'<div class="h">{c}</div>' for c in i18n.weekday_initials())]
    for d in month_days(year, month):
        sel = sel_start <= d < sel_end
        cls = "d" + (" out" if d.month != month else "") + (" today" if d == today else "") + \
              (" has" if d in busy_days else "")
        if sel:
            cls += " sel" + (" l" if d == sel_start or d.weekday() == 0 else "") + \
                   (" r" if d == sel_end - dt.timedelta(days=1) or d.weekday() == 6 else "")
        cells.append(f'<div class="{cls}"><span>{d.day}</span></div>')
    return (f'<div class="lvmini"><div class="lvmini-t">{i18n.month_name(month)} {year}</div>'
            f'<div class="lvmini-g">{"".join(cells)}</div></div>')


def legend() -> str:
    rows = "".join(f'<div class="lvleg-r"><i style="background:{COLORS[k]}"></i>{esc(t(label))}</div>' for k, label in LEGEND)
    return f'<div class="lvleg"><div class="lvleg-t">{esc(t("Calendars"))}</div>{rows}</div>'
