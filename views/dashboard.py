import datetime as dt
import streamlit as st
import cal, cases, i18n, subscription, ui
from i18n import t
from views.calendar_grid import COLORS


def _greeting() -> str:
    h = dt.datetime.now().hour
    return t("Good morning") if h < 12 else t("Good afternoon") if h < 18 else t("Good evening")


def render():
    u = st.session_state["user"]
    pages = st.session_state.get("_pages", {})
    plan = subscription.effective_plan(u)
    lim = subscription.plan_info(u)
    name = u["email"].split("@")[0].replace(".", " ").title()
    ui.page_header(f"{_greeting()}, {name}", i18n.date_full(dt.date.today()), eyebrow="Dashboard")

    my = cases.list_cases(u["id"])
    now = dt.datetime.now().timestamp()
    dls = cases.deadlines_between(u["id"], now - 86400, now + 14 * 86400)
    used = subscription.ai_used_today(u["id"])
    open_tasks = cases.my_open_tasks(u["id"])

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(ui.stat("Active cases", str(len(my)), t("of {max} on {plan}", max=lim["max_cases"],
                                                         plan=t(lim["name"]))), unsafe_allow_html=True)
    c2.markdown(ui.stat("Due in 14 days", str(len(dls)),
                        t("{n} overdue", n=sum(1 for d in dls if d["due"] < now)) if any(d["due"] < now for d in dls)
                        else "Nothing overdue"), unsafe_allow_html=True)
    c3.markdown(ui.stat("My open tasks", str(len(open_tasks)), "Assigned to you"), unsafe_allow_html=True)
    c4.markdown(ui.stat("AI requests today", f"{used} / {lim['daily_ai']}", t("{plan} plan", plan=t(lim["name"])),
                        used / max(1, lim["daily_ai"])), unsafe_allow_html=True)

    left, right = st.columns([5, 4], gap="large")
    with left:
        ui.section("Today")
        start = dt.datetime.combine(dt.date.today(), dt.time(0)).timestamp()
        today = cal.my_events(u["id"], start, start + 86400)
        rows = [ui.item(e["title"], t("Tentative") if e["my_status"] == "pending" else "",
                        f"{dt.datetime.fromtimestamp(e['start']):%H:%M} – {dt.datetime.fromtimestamp(e['end']):%H:%M}",
                        COLORS["meeting"] if e.get("attendees") or not e["mine"] else COLORS["event"])
                for e in today]
        ui.html_block(f'<div class="lv-card"><div class="lv-list">{"".join(rows)}</div>'
                      f'{"" if rows else "<div class=lv-empty>" + ui.esc(t("Nothing scheduled today.")) + "</div>"}</div>')

        ui.section("Upcoming deadlines")
        rows = []
        for d in dls:
            days = (dt.date.fromtimestamp(d["due"]) - dt.date.today()).days
            side = (t("Overdue") if d["due"] < now else t("Today") if days == 0 else t("Tomorrow") if days == 1
                    else t("In {n} days", n=days))
            color = COLORS["deadline"] if d["kind"] == "deadline" else COLORS["task"]
            rows.append(ui.item(d["title"], f"{d['case']} · {i18n.date_time(dt.datetime.fromtimestamp(d['due']))}",
                                side, color))
        ui.html_block(f'<div class="lv-card"><div class="lv-list">{"".join(rows)}</div>'
                      f'{"" if rows else "<div class=lv-empty>" + ui.esc(t("No deadlines in the next 14 days.")) + "</div>"}</div>')

    with right:
        ui.section("My open tasks")
        rows = [ui.item(tk["title"], tk["case"],
                        t("Due {date}", date=i18n.date_md(dt.datetime.fromtimestamp(tk["due"]))) if tk["due"] else "",
                        COLORS["task"]) for tk in open_tasks]
        ui.html_block(f'<div class="lv-card"><div class="lv-list">{"".join(rows)}</div>'
                      f'{"" if rows else "<div class=lv-empty>" + ui.esc(t("Nothing assigned to you.")) + "</div>"}</div>')

        ui.section("Recent cases")
        rows = [ui.item(c["title"], t(c["role"].title())) for c in my[:6]]
        ui.html_block(f'<div class="lv-card"><div class="lv-list">{"".join(rows)}</div>'
                      f'{"" if rows else "<div class=lv-empty>" + ui.esc(t("No cases yet. Create one under Cases.")) + "</div>"}</div>')
