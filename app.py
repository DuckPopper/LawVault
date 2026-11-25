"""LawVault entry point: session gate (tab state or cookie) -> navigation, presence and live notifications."""
from pathlib import Path
import streamlit as st
import auth, calsync, db, i18n, jobs, notify, presence, session_cookie, subscription, ui
from i18n import t
from views import auth_ui, dashboard, cases_ui, calendar_ui, ai_ui, admin, settings, notifications_ui, legal_ui, files_ui, news_ui, detector_ui

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
ui.inject_css(ui.valid_theme(user["theme"]) if user else st.session_state.get("theme"))  # per-user glass theme
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
    "qa": st.Page(ai_ui.qa, title=t("Legal assistant"), icon=":material/auto_awesome:", url_path="qa"),
    "docs": st.Page(ai_ui.analyzer, title=t("Document review"), icon=":material/description:", url_path="docs"),
    "notifications": st.Page(notifications_ui.render, title=t("Notifications"), icon=":material/notifications:",
                             url_path="notifications"),
    "settings": st.Page(settings.render, title=t("Settings"), icon=":material/settings:", url_path="settings"),
}
if user["role"] == "admin":
    pages["admin"] = st.Page(admin.render, title=t("Admin"), icon=":material/admin_panel_settings:",
                             url_path="admin")
nav = st.navigation({
    t("Workspace"): [pages["dashboard"], pages["cases"], pages["calendar"], pages["files"], pages["news"]],
    t("AI"): [pages["analysis"], pages["qa"], pages["docs"], pages["detector"]],
    t("You"): [pages[k] for k in ("notifications", "settings", "admin") if k in pages],
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
        st.page_link(pages["notifications"], label=i18n.plural(n, "{n} unread notification", "{n} unread notifications"),
                     icon=":material/notifications_paused:" if dnd else ":material/mark_email_unread:")
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


def _set_language():
    auth.set_language(user["id"], st.session_state["lang_choice"])


def _toggle_theme():
    auth.set_theme(user["id"], "light" if ui.valid_theme(user["theme"]) == "dark" else "dark")


def _set_presence():
    presence.set_choice(user["id"], st.session_state["presence_choice"])


with st.sidebar:
    live_bar(token)
    ai_activity(user["id"], nav.url_path)
    plan = t(subscription.plan_info(user)["name"])
    ui.html_block(f"""<div class="lv-user"><div class="lv-avatar">{ui.esc(ui.initials(user['email']))}</div>
        <div class="lv-user-meta"><div class="lv-user-email">{ui.esc(user['email'])}</div>
        <div class="lv-user-plan">{ui.esc(t("{plan} plan", plan=plan))}</div></div></div>""")
    current = presence.get_choice(user["id"])
    st.selectbox(t("Status"), presence.CHOICES, index=presence.CHOICES.index(current),
                 format_func=lambda c: t(presence.CHOICE_LABEL[c]), key="presence_choice", on_change=_set_presence,
                 label_visibility="collapsed",
                 help=t("Invisible: you appear offline. Do Not Disturb: no pop-up notifications."))
    st.selectbox(t("Language"), list(i18n.LANGS), index=list(i18n.LANGS).index(i18n.valid(user["lang"])),
                 format_func=i18n.LANGS.get, key="lang_choice", on_change=_set_language,
                 label_visibility="collapsed", help=t("Interface language"))
    dark = ui.valid_theme(user["theme"]) == "dark"
    st.button(t("Light mode") if dark else t("Dark mode"), icon=":material/light_mode:" if dark else ":material/dark_mode:",
              use_container_width=True, on_click=_toggle_theme, key="theme_toggle")
    if st.button(t("Log out"), icon=":material/logout:", use_container_width=True):
        auth.logout(token)
        keep = i18n.lang()
        st.session_state.clear()
        st.session_state["clear_cookie"] = True
        i18n.set_lang(keep)
        st.rerun()
nav.run()
