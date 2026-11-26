"""LawVault entry point: session gate (tab state or cookie) -> navigation, presence and live notifications."""
from pathlib import Path
import streamlit as st
import auth, calsync, db, i18n, jobs, notify, presence, session_cookie, subscription, ui
from i18n import t
from views import auth_ui, dashboard, cases_ui, calendar_ui, ai_ui, admin, settings, profile, account_menu, notifications_ui, legal_ui, files_ui, news_ui, detector_ui, tools_ui

ASSETS = Path(__file__).parent / "assets"
st.set_page_config(page_title="LawVault", page_icon=str(ASSETS / "icon.svg"), layout="wide")
st.logo(str(ASSETS / "logo.svg"), icon_image=str(ASSETS / "icon.svg"), size="large")
db.init_db()


@st.cache_resource
def _sync_worker():
    calsync.start_worker()      # syncs linked Google / Apple calendars every few minutes
    return True


_sync_worker()

# 1) Which session is this? Tab memory first, then the cookie (survives refresh).
token = st.session_state.get("token") or session_cookie.read()
user = auth.validate_session(token)
ui.inject_css(ui.valid_theme(user["theme"]) if user else st.session_state.get("theme"),
              subscription.accent_hue(user) if user else None)  # per-user glass theme and accent colour
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
st.session_state["theme"] = ui.valid_theme(user["theme"])
i18n.set_lang(user["lang"])  # the saved language wins over whatever the login page was showing
if st.session_state.pop("set_cookie", False):
    session_cookie.write(token)
presence.touch(user["id"])

# 2) Pages, grouped like a desktop app sidebar
unread = notify.unread_count(user["id"])  # shown on the Notifications entry
pages = {
    "dashboard": st.Page(dashboard.render, title=t("Dashboard"), icon=":material/space_dashboard:",
                         url_path="dashboard", default=True),
    "cases": st.Page(cases_ui.render, title=t("Cases"), icon=":material/gavel:", url_path="cases"),
    "calendar": st.Page(calendar_ui.render, title=t("Calendar"), icon=":material/calendar_month:",
                        url_path="calendar"),
    "analysis": st.Page(legal_ui.render, title=t("Case analysis"), icon=":material/troubleshoot:",
                        url_path="analysis"),
    "files": st.Page(files_ui.render, title=t("Files"), icon=":material/folder_open:", url_path="files"),
    "news": st.Page(news_ui.render, title=t("News"), icon=":material/newspaper:", url_path="news"),
    "detector": st.Page(detector_ui.render, title=t("AI detector"), icon=":material/fingerprint:",
                        url_path="detector"),
    "tools": st.Page(tools_ui.render, title=t("Tools"), icon=":material/build:", url_path="tools"),
    "qa": st.Page(ai_ui.qa, title=t("Legal assistant"), icon=":material/auto_awesome:", url_path="qa"),
    "docs": st.Page(ai_ui.analyzer, title=t("Document review"), icon=":material/description:", url_path="docs"),
    "profile": st.Page(profile.render, title=t("Profile"), icon=":material/account_circle:", url_path="profile"),
    "notifications": st.Page(notifications_ui.render, title=t("Notifications"), icon=":material/notifications:",
                             url_path="notifications"),
    "settings": st.Page(settings.render, title=t("Settings"), icon=":material/settings:", url_path="settings"),
}
if user["role"] == "admin":
    pages["admin"] = st.Page(admin.render, title=t("Admin"), icon=":material/admin_panel_settings:",
                             url_path="admin")
GROUPS = [(t("Workspace"), ["dashboard", "cases", "calendar", "files", "tools", "news"]),
          (t("AI"), ["analysis", "qa", "docs", "detector"])]
# Every page is registered, but the list in the sidebar is drawn by hand (account_menu.nav): Profile,
# Notifications, Settings and Admin are reached from the account menu only.
nav = st.navigation(list(pages.values()), position="hidden")
# Older notification links point at the pages that now live inside Settings
pages["account"] = pages["privacy"] = pages["settings"]
st.session_state["_pages"] = pages


@st.fragment(run_every=30)
def live_bar(tok: str):
    """Runs every 30 s: keeps 'online' status fresh and pops up new notifications."""
    u = auth.peek_session(tok)
    if not u:
        st.rerun()  # session ended elsewhere (logged out / expired) -> back to login
    presence.heartbeat(u["id"])
    dnd = presence.is_dnd(u["id"])
    toasts = notify.take_toasts(u["id"])
    if not dnd:  # Do Not Disturb: still saved in the bell, just no pop-ups
        for toast in toasts:
            st.toast(f"{toast['icon']} {i18n.tm(toast['text'])}")


def ai_activity(uid: str, here: str):
    """Sidebar status for AI work running in the background. Pops a toast when a job finishes on another page."""
    if not jobs.for_user(uid):
        return

    @st.fragment(run_every=2)
    def _show():
        for j in jobs.for_user(uid):
            page = pages[jobs.PAGE[j["kind"]]]
            if j["running"]:
                st.page_link(page, label=t("{job}: working…", job=ui.job_label(j)), icon=":material/hourglass_top:")
            elif jobs.PAGE[j["kind"]] != here:  # the job's own page shows the result itself
                jobs.mark_seen(uid, j["kind"], j["key"])
                msg = "{job} failed. Open {page} to see it." if j["error"] else "{job} is ready. Open {page} to see it."
                st.toast(t(msg, job=ui.job_label(j), page=page.title),
                         icon=":material/error:" if j["error"] else ":material/task_alt:")
    _show()


with st.sidebar:
    account_menu.render(user, token, pages, unread)
    account_menu.nav(pages, GROUPS, nav.title)
    live_bar(token)
    account_menu.clock(user)
    account_menu.settings_link(pages)
    ai_activity(user["id"], nav.url_path)
nav.run()
