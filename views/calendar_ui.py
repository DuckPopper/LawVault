"""Calendar page: Apple Calendar-style Day / Week / Month views plus invites, team calendars, find-a-time, sharing."""
import datetime as dt
import streamlit as st
import cal, cases, ui
from views import calendar_grid as grid

LEVEL_LABEL = {"busy": "Busy only", "details": "Titles visible", "full": "Full"}
VIS_HELP = {
    "private": "**Private.** Nobody sees your calendar unless you approve their request.",
    "busy": "**Busy only.** Case teammates see *when* you're busy, never *what*.",
    "details": "**Details.** Case teammates see event titles. Private notes stay hidden.",
}
VIEWS = ["Day", "Week", "Month"]

_CSS = """<style>
.lv-calt{ font-size:1.9rem; letter-spacing:-.025em; line-height:1.1; color:var(--lv-text); font-weight:700; }
.lv-calt span{ font-weight:400; color:var(--lv-muted); }
.st-key-cal_toolbar [data-testid="stButton"] button{ min-height:2.2rem; }
.st-key-cal_side{ position:sticky; top:4rem; }
.lv-dayrow{ display:flex; gap:.8rem; align-items:center; }
.lv-dayrow i{ width:9px; height:9px; border-radius:50%; flex-shrink:0; }
.lv-dayh{ font-size:.75rem; letter-spacing:.08em; text-transform:uppercase; color:var(--lv-muted); font-weight:600; margin:.9rem 0 .2rem; }
</style>"""


def _fmt(ts, f="%H:%M"):
    return dt.datetime.fromtimestamp(ts).strftime(f)


# ---------- state ----------
def _view() -> str:
    v = st.session_state.get("cal_view") or st.session_state.get("_cal_view_last") or "Week"
    st.session_state["_cal_view_last"] = v
    return v


def _keep_view():
    """Clicking the selected segment again would deselect it; keep the last view instead."""
    if not st.session_state.get("cal_view"):
        st.session_state["cal_view"] = st.session_state.get("_cal_view_last", "Week")


def _anchor() -> dt.date:
    return st.session_state.setdefault("cal_anchor", dt.date.today())


def _range(view: str, anchor: dt.date):
    """Visible [first, last) dates for a view."""
    if view == "Day":
        return anchor, anchor + dt.timedelta(days=1)
    if view == "Week":
        mon = anchor - dt.timedelta(days=anchor.weekday())
        return mon, mon + dt.timedelta(days=7)
    days = grid.month_days(anchor.year, anchor.month)
    return days[0], days[-1] + dt.timedelta(days=1)


def _shift(step: int):
    view, a = _view(), _anchor()
    if view == "Day":
        a += dt.timedelta(days=step)
    elif view == "Week":
        a += dt.timedelta(days=7 * step)
    else:
        m = a.month - 1 + step
        a = dt.date(a.year + m // 12, m % 12 + 1, 1)
    st.session_state["cal_anchor"] = a


def _go_today():
    st.session_state["cal_anchor"] = dt.date.today()


def _jump():
    if st.session_state.get("cal_jump"):
        st.session_state["cal_anchor"] = st.session_state["cal_jump"]


def _title(view: str, first: dt.date, last_excl: dt.date, anchor: dt.date) -> str:
    if view == "Day":
        return f"{anchor:%B} {anchor.day}, <span>{anchor.year}</span>"
    if view == "Month":
        return f"{anchor:%B} <span>{anchor.year}</span>"
    last = last_excl - dt.timedelta(days=1)
    if first.month == last.month:
        return f"{first:%B} <span>{first.year}</span>"
    if first.year == last.year:
        return f"{first:%b} – {last:%b} <span>{first.year}</span>"
    return f"{first:%b} <span>{first.year}</span> – {last:%b} <span>{last.year}</span>"


# ---------- data ----------
def _my_items(u, start: float, end: float):
    items = []
    for e in cal.my_events(u["id"], start, end):
        kind = "meeting" if (e.get("attendees") or not e["mine"]) else "event"
        sub = "" if e["mine"] else f"from {e['organizer']}"
        items.append(dict(e, kind=kind, tentative=e["my_status"] == "pending", sub=sub))
    for d in cases.deadlines_between(u["id"], start, end):
        items.append(dict(id=None, title=d["title"], start=d["due"], end=d["due"] + 1800, kind=d["kind"],
                          tentative=False, sub=d["case"], mine=False, notes="", attendees=[], my_status=None))
    return sorted(items, key=lambda e: e["start"])


# ---------- dialogs ----------
@st.dialog("New event")
def _new_event_dialog(u, default_day: dt.date):
    mates = cal.teammates(u["id"])
    my_cases = cases.list_cases(u["id"])
    with st.form("new_event", border=False):
        title = st.text_input("Title", placeholder="Client call: Smith v. Acme")
        c1, c2, c3 = st.columns([2, 1, 1])
        day = c1.date_input("Date", value=default_day)
        t1 = c2.time_input("Starts", value=dt.time(10, 0), step=900)
        t2 = c3.time_input("Ends", value=dt.time(11, 0), step=900)
        inv = st.multiselect("Invitees", [m["id"] for m in mates],
                             format_func=lambda i: next(m["email"] for m in mates if m["id"] == i),
                             placeholder="Add people you share a case with")
        case = st.selectbox("Case", [None] + [c["id"] for c in my_cases],
                            format_func=lambda i: "None" if i is None else next(c["title"] for c in my_cases
                                                                                if c["id"] == i))
        notes = st.text_area("Notes", placeholder="Only you and invitees can see these", height=90)
        if st.form_submit_button("Add event", type="primary", use_container_width=True):
            s = dt.datetime.combine(day, t1).timestamp()
            e = dt.datetime.combine(day, t2).timestamp()
            eid, msg = cal.add_event(u, title, s, e, notes, case, inv)
            if eid:
                st.session_state["cal_anchor"] = day
                st.session_state["cal_flash"] = msg
                st.rerun()
            st.error(msg)


# ---------- event list under the grid ----------
def _event_list(u, items, key: str, editable: bool):
    if not items:
        st.caption("Nothing scheduled in this range.")
        return
    day = None
    for e in items:
        d = dt.date.fromtimestamp(e["start"])
        if d != day:
            day = d
            ui.html_block(f'<div class="lv-dayh">{d:%A, %B} {d.day}</div>')
        color = grid.COLORS.get(e["kind"], grid.COLORS["event"])
        when = _fmt(e["start"]) if e["kind"] in ("deadline", "task") else f"{_fmt(e['start'])} – {_fmt(e['end'])}"
        tags = []
        if e.get("tentative"):
            tags.append('<span class="lv-pill grey">Tentative</span>')
        if e["kind"] == "deadline":
            tags.append('<span class="lv-pill red">Deadline</span>')
        a, b = st.columns([8, 1], vertical_alignment="center")
        a.markdown(f'<div class="lv-dayrow"><i style="background:{color}"></i><div><div class="lv-row-t">'
                   f'{ui.esc(e["title"])} {" ".join(tags)}</div><div class="lv-row-d">{ui.esc(when)}'
                   f'{" · " + ui.esc(e["sub"]) if e.get("sub") else ""}</div></div></div>', unsafe_allow_html=True)
        if editable and e.get("id"):
            with b.popover("", icon=":material/more_horiz:", use_container_width=True):
                st.markdown(f"**{e['title']}**")
                st.caption(f"{_fmt(e['start'], '%a %b %d')} · {when}")
                if e.get("notes"):
                    st.caption(e["notes"])
                if e.get("organizer") and not e["mine"]:
                    st.caption(f"Organizer: {e['organizer']}")
                for att in e.get("attendees", []):
                    st.caption(f"{att['email']}: {att['status']}")
                if e.get("tentative"):
                    c1, c2 = st.columns(2)
                    if c1.button("Accept", key=f"ac_{key}_{e['id']}", type="primary", use_container_width=True):
                        cal.respond_invite(u["id"], e["id"], True)
                        st.rerun()
                    if c2.button("Decline", key=f"dc_{key}_{e['id']}", use_container_width=True):
                        cal.respond_invite(u["id"], e["id"], False)
                        st.rerun()
                elif st.button("Delete for everyone" if e["mine"] else "Remove from my calendar",
                               key=f"del_{key}_{e['id']}", use_container_width=True):
                    cal.delete_event(u["id"], e["id"])
                    st.rerun()


# ---------- main calendar ----------
def _calendar(u):
    view, anchor = _view(), _anchor()
    first, last = _range(view, anchor)
    start = dt.datetime.combine(first, dt.time(0)).timestamp()
    end = dt.datetime.combine(last, dt.time(0)).timestamp()
    items = _my_items(u, start, end)

    with st.container(key="cal_toolbar"):
        t, seg, nav, add = st.columns([5, 3, 2.6, 1.6], vertical_alignment="center")
        t.markdown(f'<div class="lv-calt">{_title(view, first, last, anchor)}</div>', unsafe_allow_html=True)
        seg.segmented_control("View", VIEWS, default="Week", key="cal_view", on_change=_keep_view,
                              label_visibility="collapsed")
        p, td, n = nav.columns([1, 1.7, 1])
        p.button("", icon=":material/chevron_left:", key="cal_prev", on_click=_shift, args=(-1,),
                 use_container_width=True, help="Previous")
        td.button("Today", key="cal_today", on_click=_go_today, use_container_width=True)
        n.button("", icon=":material/chevron_right:", key="cal_next", on_click=_shift, args=(1,),
                 use_container_width=True, help="Next")
        if add.button("New", icon=":material/add:", type="primary", key="cal_new", use_container_width=True):
            today = dt.date.today()
            _new_event_dialog(u, today if first <= today < last else (anchor if view == "Day" else first))
    flash = st.session_state.pop("cal_flash", None)
    if flash:
        st.toast(flash)

    side, main = st.columns([1, 4.3], gap="medium")
    with side, st.container(key="cal_side"):
        m0 = dt.date(anchor.year, anchor.month, 1)
        mdays = grid.month_days(m0.year, m0.month)
        ms = dt.datetime.combine(mdays[0], dt.time(0)).timestamp()
        mitems = _my_items(u, ms, ms + 42 * 86400)
        busy = {dt.date.fromtimestamp(e["start"]) for e in mitems}
        st.markdown(grid.mini_month(m0.year, m0.month, first if view != "Month" else m0,
                                    last if view != "Month" else m0, busy), unsafe_allow_html=True)
        st.date_input("Go to date", value=None, key="cal_jump", on_change=_jump, format="YYYY-MM-DD",
                      label_visibility="collapsed")
        st.markdown(grid.legend(), unsafe_allow_html=True)
        n_inv = len(cal.pending_invites(u["id"]))
        if n_inv:
            st.caption(f"{n_inv} invitation{'s' if n_inv != 1 else ''} waiting in Invites.")

    with main:
        if view == "Month":
            st.markdown(grid.month_grid(anchor.year, anchor.month, items), unsafe_allow_html=True)
        else:
            days = [first + dt.timedelta(days=i) for i in range((last - first).days)]
            st.markdown(grid.time_grid(days, items), unsafe_allow_html=True)
        label = {"Day": "this day", "Week": "this week", "Month": "this month"}[view]
        visible = items if view != "Month" else [
            e for e in items if dt.date.fromtimestamp(e["start"]).month == anchor.month]
        with st.expander(f"Events {label} · {len(visible)}", expanded=view == "Day"):
            _event_list(u, visible, "mine", editable=True)


# ---------- other tabs ----------
def _invites(u, invites):
    if not invites:
        st.info("No pending invitations.", icon=":material/event_available:")
        return
    for e in invites:
        with st.container(border=True):
            a, b, c = st.columns([6, 1.2, 1.2], vertical_alignment="center")
            a.markdown(f'<div class="lv-row-t">{ui.esc(e["title"])}</div><div class="lv-row-d">'
                       f'{_fmt(e["start"], "%A, %B %d · %H:%M")} – {_fmt(e["end"])} · from {ui.esc(e["organizer"])}'
                       f'</div>', unsafe_allow_html=True)
            if e["notes"]:
                a.caption(e["notes"])
            if b.button("Accept", key=f"acc_{e['id']}", type="primary", use_container_width=True):
                cal.respond_invite(u["id"], e["id"], True)
                st.rerun()
            if c.button("Decline", key=f"dec_{e['id']}", use_container_width=True):
                cal.respond_invite(u["id"], e["id"], False)
                st.rerun()


def _team(u):
    vis = cal.viewable_calendars(u["id"])
    if not vis:
        st.info("You can't see anyone's calendar yet. Teammates can turn on sharing, or you can request access "
                "under Sharing.", icon=":material/visibility_off:")
        return
    a, b = st.columns([3, 2], vertical_alignment="bottom")
    who = a.selectbox("Calendar", [v["id"] for v in vis],
                      format_func=lambda i: next(f"{v['email']}  ·  {LEVEL_LABEL[v['level']]}"
                                                 for v in vis if v["id"] == i))
    wk = st.session_state.setdefault("team_week", dt.date.today() - dt.timedelta(days=dt.date.today().weekday()))
    p, t, n, lbl = b.columns([1, 1.6, 1, 3], vertical_alignment="center")
    if p.button("", icon=":material/chevron_left:", key="tw_prev", use_container_width=True):
        st.session_state["team_week"] = wk - dt.timedelta(days=7)
        st.rerun()
    if t.button("Today", key="tw_today", use_container_width=True):
        st.session_state.pop("team_week")
        st.rerun()
    if n.button("", icon=":material/chevron_right:", key="tw_next", use_container_width=True):
        st.session_state["team_week"] = wk + dt.timedelta(days=7)
        st.rerun()
    lbl.markdown(f"**{wk:%b %d} – {wk + dt.timedelta(days=6):%b %d}**")
    start = dt.datetime.combine(wk, dt.time(0)).timestamp()
    level, evs = cal.view_calendar(u["id"], who, start, start + 7 * 86400)
    items = [dict(e, kind="busy" if level == "busy" or e["id"] is None else "event", tentative=False, sub="")
             for e in evs]
    if level == "busy":
        st.caption("This person shares free/busy only: you see when they're busy, not what.")
    st.markdown(grid.time_grid([wk + dt.timedelta(days=i) for i in range(7)], items), unsafe_allow_html=True)


def _find(u):
    st.caption(f"Finds times when everyone is free, Monday to Friday, {cal.WORK_START}:00–{cal.WORK_END}:00. "
               "Only people whose calendar you can see are listed.")
    vis = cal.viewable_calendars(u["id"])
    with st.form("find"):
        people = st.multiselect("Attendees", [v["id"] for v in vis],
                                format_func=lambda i: next(v["email"] for v in vis if v["id"] == i))
        c1, c2, c3 = st.columns(3)
        dur = c1.selectbox("Duration", [30, 60, 90, 120], index=1, format_func=lambda m: f"{m} min")
        first = c2.date_input("From", value=dt.date.today())
        days = c3.slider("Days to search", 1, 14, 5)
        title = st.text_input("Meeting title", value="Case strategy meeting")
        go = st.form_submit_button("Find free slots", type="primary")
    if go:
        slots, err = cal.find_slots(u, people, first, days, dur)
        st.session_state["slots"] = dict(slots=slots, err=err, people=people, title=title)
    res = st.session_state.get("slots")
    if not res:
        return
    if res["err"]:
        st.error(res["err"])
    elif not res["slots"]:
        st.warning("No common free time in that range. Try more days or a shorter meeting.")
    else:
        st.success(f"{len(res['slots'])} slots where everyone is free.")
        for s, e in res["slots"]:
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.markdown(f"{_fmt(s, '%a %b %d')} · **{_fmt(s)} – {_fmt(e)}**")
            if c2.button("Book", key=f"book_{s}", use_container_width=True):
                eid, msg = cal.add_event(u, res["title"], s, e, "", None, res["people"])
                (st.success if eid else st.error)(msg)
                if eid:
                    st.session_state.pop("slots")


def _sharing(u, reqs):
    ui.section("Who can see my calendar")
    cur = cal.get_visibility(u["id"])
    choice = st.radio("Visibility for case teammates", cal.VISIBILITY, index=cal.VISIBILITY.index(cur),
                      format_func=lambda v: VIS_HELP[v], key="vis", label_visibility="collapsed")
    if choice != cur:
        cal.set_visibility(u["id"], choice)
        st.toast("Calendar visibility saved.")

    ui.section("Requests to see my calendar")
    if not reqs:
        st.caption("No pending requests.")
    for r in reqs:
        with st.container(border=True):
            a, b, c, d = st.columns([5, 1.3, 1.3, 1.3], vertical_alignment="center")
            a.markdown(f"**{r['email']}** wants {LEVEL_LABEL[r['level']].lower()} access")
            if b.button("Approve", key=f"ap_{r['viewer_id']}", type="primary", use_container_width=True):
                cal.respond_request(u["id"], r["viewer_id"], True)
                st.rerun()
            if r["level"] == "details" and c.button("Busy only", key=f"apb_{r['viewer_id']}",
                                                     use_container_width=True):
                cal.respond_request(u["id"], r["viewer_id"], True, "busy")
                st.rerun()
            if d.button("Deny", key=f"dn_{r['viewer_id']}", use_container_width=True):
                cal.respond_request(u["id"], r["viewer_id"], False)
                st.rerun()

    granted = cal.granted_viewers(u["id"])
    if granted:
        ui.section("People I approved")
        for g in granted:
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.write(f"{g['email']} · {LEVEL_LABEL[g['level']]}")
            if c2.button("Revoke", key=f"rv_{g['viewer_id']}", use_container_width=True):
                cal.revoke(u["id"], g["viewer_id"])
                st.rerun()

    ui.section("Request a colleague's calendar")
    mates = cal.teammates(u["id"])
    if not mates:
        st.caption("Share a case with someone first. You can only request calendars of case teammates.")
    else:
        with st.form("req"):
            who = st.selectbox("Colleague", [m["id"] for m in mates],
                               format_func=lambda i: next(m["email"] for m in mates if m["id"] == i))
            lvl = st.radio("Access", ["busy", "details"], format_func=lambda v: LEVEL_LABEL[v], horizontal=True)
            if st.form_submit_button("Send request"):
                ok, msg = cal.request_access(u["id"], who, lvl)
                (st.success if ok else st.warning)(msg)
    mine = cal.my_requests(u["id"])
    if mine:
        ui.section("My requests")
        for r in mine:
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.write(f"{r['email']} · {LEVEL_LABEL[r['level']]} · *{r['status']}*")
            if c2.button("Withdraw" if r["status"] == "pending" else "Stop viewing", key=f"cx_{r['owner_id']}",
                         use_container_width=True):
                cal.cancel_request(u["id"], r["owner_id"])
                st.rerun()


def render():
    u = st.session_state["user"]
    st.markdown(grid.CSS + _CSS, unsafe_allow_html=True)
    invites = cal.pending_invites(u["id"])
    reqs = cal.incoming_requests(u["id"])
    t_cal, t_inv, t_team, t_find, t_share = st.tabs([
        "Calendar", f"Invites{f' · {len(invites)}' if invites else ''}", "Team calendars", "Find a time",
        f"Sharing{f' · {len(reqs)}' if reqs else ''}"])
    with t_cal:
        _calendar(u)
    with t_inv:
        _invites(u, invites)
    with t_team:
        _team(u)
    with t_find:
        _find(u)
    with t_share:
        _sharing(u, reqs)
