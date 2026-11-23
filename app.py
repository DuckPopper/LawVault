"""LawVault entry point: session gate (tab state or cookie) -> navigation, presence and live notifications."""
from pathlib import Path
import streamlit as st
import auth, db, jobs, notify, presence, session_cookie, subscription, ui
from views import auth_ui, dashboard, cases_ui, calendar_ui, ai_ui, admin, settings, notifications_ui, legal_ui

ASSETS = Path(__file__).parent / "assets"
st.set_page_config(page_title="LawVault", page_icon=str(ASSETS / "icon.svg"), layout="wide")
st.logo(str(ASSETS / "logo.svg"), icon_image=str(ASSETS / "icon.svg"), size="large")
ui.inject_css()
db.init_db()

# 1) Which session is this? Tab memory first, then the cookie (survives refresh).
token = st.session_state.get("token") or session_cookie.read()
user = auth.validate_session(token)
if not user:
    if st.session_state.get("token"):
        st.toast("Session expired. Please log in again.")
    st.session_state.pop("token", None)
    st.session_state.pop("user", None)
    if st.session_state.pop("clear_cookie", False) or token:
        session_cookie.clear()
    auth_ui.render()
    st.stop()

st.session_state["token"] = token
st.session_state["user"] = user
if st.session_state.pop("set_cookie", False):
    session_cookie.write(token)
presence.touch(user["id"])

# 2) Pages, grouped like a desktop app sidebar
pages = {
    "dashboard": st.Page(dashboard.render, title="Dashboard", icon=":material/space_dashboard:",
                         url_path="dashboard", default=True),
    "cases": st.Page(cases_ui.render, title="Cases", icon=":material/gavel:", url_path="cases"),
    "calendar": st.Page(calendar_ui.render, title="Calendar", icon=":material/calendar_month:", url_path="calendar"),
    "analysis": st.Page(legal_ui.render, title="Case analysis", icon=":material/troubleshoot:",
                        url_path="analysis"),
    "qa": st.Page(ai_ui.qa, title="Legal assistant", icon=":material/auto_awesome:", url_path="qa"),
    "docs": st.Page(ai_ui.analyzer, title="Document review", icon=":material/description:", url_path="docs"),
    "notifications": st.Page(notifications_ui.render, title="Notifications", icon=":material/notifications:",
                             url_path="notifications"),
    "settings": st.Page(settings.render, title="Settings", icon=":material/settings:", url_path="settings"),
}
if user["role"] == "admin":
    pages["admin"] = st.Page(admin.render, title="Admin", icon=":material/admin_panel_settings:", url_path="admin")
nav = st.navigation({
    "Workspace": [pages["dashboard"], pages["cases"], pages["calendar"]],
    "AI": [pages["analysis"], pages["qa"], pages["docs"]],
    "You": [pages[k] for k in ("notifications", "settings", "admin") if k in pages],
})
# Older notification links point at the pages that now live inside Settings
pages["account"] = pages["privacy"] = pages["settings"]
st.session_state["_pages"] = pages


@st.fragment(run_every=30)
def live_bar(tok: str):
    """Runs every 30 s: keeps 'online' status fresh, updates the unread badge, pops up new notifications."""
    u = auth.peek_session(tok)
    if not u:
        st.rerun()  # session ended elsewhere (logged out / expired) -> back to login
    presence.heartbeat(u["id"])
    dnd = presence.is_dnd(u["id"])
    n = notify.unread_count(u["id"])
    if n:
        st.page_link(pages["notifications"], label=f"{n} unread notification{'s' if n != 1 else ''}",
                     icon=":material/notifications_paused:" if dnd else ":material/mark_email_unread:")
    toasts = notify.take_toasts(u["id"])
    if not dnd:  # Do Not Disturb: still saved in the bell, just no pop-ups
        for t in toasts:
            st.toast(f"{t['icon']} {t['text']}")


def ai_activity(uid: str, here: str):
    """Sidebar status for AI work running in the background. Pops a toast when a job finishes on another page."""
    if not jobs.for_user(uid):
        return

    @st.fragment(run_every=2)
    def _show():
        for j in jobs.for_user(uid):
            page = pages[jobs.PAGE[j["kind"]]]
            if j["running"]:
                st.page_link(page, label=f"{j['label']}: working…", icon=":material/hourglass_top:")
            elif jobs.PAGE[j["kind"]] != here:  # the job's own page shows the result itself
                jobs.mark_seen(uid, j["kind"], j["key"])
                done = "failed" if j["error"] else "ready"
                st.toast(f"{j['label']} {done}. Open {page.title} to see it.",
                         icon=":material/error:" if j["error"] else ":material/task_alt:")
    _show()


def _set_presence():
    presence.set_choice(user["id"], st.session_state["presence_choice"])


with st.sidebar:
    live_bar(token)
    ai_activity(user["id"], nav.url_path)
    plan = subscription.PLANS[subscription.effective_plan(user)]["name"]
    ui.html_block(f"""<div class="lv-user"><div class="lv-avatar">{ui.esc(ui.initials(user['email']))}</div>
        <div class="lv-user-meta"><div class="lv-user-email">{ui.esc(user['email'])}</div>
        <div class="lv-user-plan">{ui.esc(plan)} plan</div></div></div>""")
    current = presence.get_choice(user["id"])
    st.selectbox("Status", presence.CHOICES, index=presence.CHOICES.index(current),
                 format_func=presence.CHOICE_LABEL.get, key="presence_choice", on_change=_set_presence,
                 label_visibility="collapsed",
                 help="Invisible: you appear offline. Do Not Disturb: no pop-up notifications.")
    if st.button("Log out", icon=":material/logout:", use_container_width=True):
        auth.logout(token)
        st.session_state.clear()
        st.session_state["clear_cookie"] = True
        st.rerun()
nav.run()
