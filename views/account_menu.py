"""The account card at the top of the sidebar and its flyout, modelled on Microsoft Teams' profile menu.

Card: avatar with a presence ring, your name and your status (or status message), an unread badge.
Flyout: who you are, availability (six statuses, each with a "clear after"), a status message, then
Notifications, Settings, Admin and Log out. Profile / Notifications / Settings / Admin are not in the side list.
"""
import datetime as dt
import streamlit as st
import auth, i18n, presence, subscription, ui
from i18n import t
from views.profile import display_name

# Material icon + colour per status (Teams uses a check, a dot, a minus, clocks and a cross)
_ICON = {"online": "check_circle", "busy": "circle", "dnd": "do_not_disturb_on", "brb": "schedule",
         "away": "schedule", "invisible": "cancel"}


def _css(initials: str, ring: str, unread: int, current: str) -> str:
    ini = "".join(ch for ch in initials if ch.isalnum())[:2]
    badge = (f'.st-key-acct [data-testid="stPopoverButton"]::after{{content:"{min(unread, 99)}";}}' if unread else
             '.st-key-acct [data-testid="stPopoverButton"]::after{display:none;}')
    icons = "".join(
        f'.st-key-pm_st_{c} [data-testid="stIconMaterial"]{{color:{presence.DOT_COLOR[c]} !important;}}'
        for c in presence.CHOICES)
    return f"""<style>
.st-key-acct [data-testid="stPopoverButton"]::before{{ content:"{ini}"; box-shadow:0 0 0 2px var(--lv-pop), 0 0 0 4px {ring}; }}
{badge}
{icons}
.st-key-pm_st_{current} button{{ background: var(--lv-surface-2) !important; }}
.st-key-pm_st_{current} button p{{ font-weight:600 !important; }}
.st-key-pm_st_{current} button::after{{ content:"✓"; margin-left:auto; color: var(--lv-accent); font-weight:700; }}
.lv-pm-av::after{{ background:{ring}; }}
</style>"""


def _logout(token: str):
    auth.logout(token)
    keep = i18n.lang()
    st.session_state.clear()
    st.session_state["clear_cookie"] = True
    i18n.set_lang(keep)


def render(user, token: str, pages: dict, unread: int):
    uid = user["id"]
    current = presence.get_choice(uid)
    seen = presence.status_of([uid]).get(uid, "offline")
    ring = presence.DOT_COLOR["invisible" if current == "invisible" else current if current != "online" else seen]
    msg = presence.get_message(uid)
    name = display_name(user)
    plan = t(subscription.plan_info(user)["name"])
    status_text = t(presence.MENU_LABEL[current])
    st.markdown(_css(ui.initials(user["email"]), ring, unread, current), unsafe_allow_html=True)

    with st.container(key="acct"), st.popover(f"{name}  \n{msg or status_text}", use_container_width=True):
        # --- who you are ---
        ui.html_block(f"""<div class="lv-pm-head">
            <div class="lv-pm-av">{ui.esc(ui.initials(user['email']))}</div>
            <div class="lv-pm-who"><div class="lv-pm-name">{ui.esc(name)}</div>
            <div class="lv-pm-mail">{ui.esc(user['email'])}</div>
            <div class="lv-pm-plan">{ui.esc(t("{plan} plan", plan=plan))}
            {' · ' + ui.esc(user['job_title']) if user['job_title'] else ''}</div></div></div>""")
        with st.container(key="pm_links_top"):
            st.page_link(pages["profile"], label=t("View profile"), icon=":material/account_circle:")

        # --- availability ---
        ui.html_block(f'<div class="lv-pm-label">{ui.esc(t("Availability"))}</div>')
        for c in presence.CHOICES:
            st.button(t(presence.MENU_LABEL[c]), key=f"pm_st_{c}", icon=f":material/{_ICON[c]}:",
                      use_container_width=True, on_click=presence.set_choice, args=(uid, c))
        if current != "online":
            until = presence.get_until(uid)
            ui.html_block(f'<div class="lv-pm-label">{ui.esc(t("Clear status after"))}</div>')
            with st.container(key="pm_dur"):
                st.selectbox(t("Clear status after"), presence.DURATIONS, index=None, label_visibility="collapsed",
                             placeholder=(t("Until {time}", time=i18n.date_time(dt.datetime.fromtimestamp(until)))
                                          if until else t("Until I change it")),
                             format_func=lambda d: t(presence.DURATION_LABEL[d]), key="pm_duration",
                             on_change=lambda: presence.set_duration(uid, st.session_state["pm_duration"] or "forever"))
            st.button(t("Reset status"), key="pm_reset", icon=":material/restart_alt:", use_container_width=True,
                      on_click=presence.reset, args=(uid,))

        # --- status message ---
        ui.html_block(f'<div class="lv-pm-label">{ui.esc(t("Status message"))}</div>')
        with st.container(key="pm_msg"):
            a, b = st.columns([5, 1], vertical_alignment="center")
            a.text_input(t("Status message"), value=msg, max_chars=presence.MESSAGE_MAX, key="pm_message",
                         placeholder=t("What are you up to?"), label_visibility="collapsed",
                         on_change=lambda: presence.set_message(uid, st.session_state["pm_message"]))
            b.button("", key="pm_msg_clear", icon=":material/close:", help=t("Clear status message"),
                     disabled=not msg, on_click=lambda: (presence.set_message(uid, ""),
                                                         st.session_state.update(pm_message="")))

        # --- go to ---
        ui.html_block('<div class="lv-pm-sep"></div>')
        with st.container(key="pm_links"):
            st.page_link(pages["notifications"], icon=":material/notifications:",
                         label=t("Notifications") + (f"  ·  {unread}" if unread else ""))
            st.page_link(pages["settings"], label=t("Settings"), icon=":material/settings:")
            if "admin" in pages:
                st.page_link(pages["admin"], label=t("Admin"), icon=":material/admin_panel_settings:")
        ui.html_block('<div class="lv-pm-sep"></div>')
        if st.button(t("Log out"), key="pm_logout", icon=":material/logout:", use_container_width=True):
            _logout(token)
            st.rerun()


def nav(pages: dict, groups: list, here_title: str):
    """The side list (Workspace, AI). Built by hand so the account pages never show up in it."""
    for title, keys in groups:
        ui.html_block(f'<div class="lv-navsec">{ui.esc(title)}</div>')
        for k in keys:
            with st.container(key=f"nav_{k}{'_on' if pages[k].title == here_title else ''}"):
                st.page_link(pages[k], label=pages[k].title, icon=pages[k].icon)
