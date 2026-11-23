import datetime as dt
import streamlit as st
import i18n, notify, presence, ui
from i18n import t

# Notifications created before Settings existed link to "account" / "privacy"
_SETTINGS_SECTION = {"account": "Account", "privacy": "Privacy", "settings": "General"}


def _ago(ts: float) -> str:
    s = int(dt.datetime.now().timestamp() - ts)
    if s < 60:
        return t("Just now")
    if s < 3600:
        return t("{n} min ago", n=s // 60)
    if s < 86400:
        return t("{n} h ago", n=s // 3600)
    return i18n.date_md(dt.datetime.fromtimestamp(ts))


def render():
    u = st.session_state["user"]
    pages = st.session_state.get("_pages", {})
    items = notify.recent(u["id"])
    unread = sum(1 for n in items if not n["read"])
    head, actions = st.columns([3, 2], vertical_alignment="bottom")
    with head:
        ui.page_header("Notifications", t("{n} unread", n=unread) if unread else "You're all caught up.")
    if items:
        a, b = actions.columns(2)
        if a.button(t("Mark all read"), icon=":material/done_all:", use_container_width=True, disabled=not unread):
            notify.mark_read(u["id"])
            st.rerun()
        if b.button(t("Clear all"), icon=":material/delete_sweep:", use_container_width=True):
            notify.clear(u["id"])
            st.rerun()
    if presence.is_dnd(u["id"]):
        st.info(t("Do Not Disturb is on. Notifications are collected here but won't pop up."),
                icon=":material/do_not_disturb_on:")
    if not items:
        return
    with st.container(border=True):
        for i, n in enumerate(items):
            if i:
                st.divider()
            a, b = st.columns([6, 1], vertical_alignment="center")
            count = f"  ×{n['count']}" if n["count"] > 1 else ""
            weight = 600 if not n["read"] else 400
            dot = '<span style="color:var(--lv-accent)">●</span>&nbsp; ' if not n["read"] else ""
            a.markdown(f'<div class="lv-row-t" style="font-weight:{weight}">{dot}{ui.esc(n["icon"])} '
                       f'{ui.esc(i18n.tm(n["text"]))}{ui.esc(count)}</div>'
                       f'<div class="lv-item-sub">{_ago(n["ts"])}</div>', unsafe_allow_html=True)
            if n["link"] in pages and b.button(t("Open"), key=f"open_{n['id']}", use_container_width=True):
                notify.mark_read(u["id"], n["id"])
                if n["link"] in _SETTINGS_SECTION:
                    st.session_state["settings_section"] = _SETTINGS_SECTION[n["link"]]
                st.switch_page(pages[n["link"]])
