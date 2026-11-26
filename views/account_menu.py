"""The account card at the top of the sidebar and its flyout, modelled on Microsoft Teams' profile menu.

Card: avatar with a presence ring, your name and your status (or status message), an unread badge.
Flyout: who you are, availability (six statuses, each with a "clear after"), a status message, then
Notifications, Settings, Admin and Log out. Profile / Notifications / Settings / Admin are not in the side list.
"""
import datetime as dt
import streamlit as st
import streamlit.components.v1 as components
import auth, i18n, presence, subscription, ui
from i18n import t
from views.profile import display_name

CLOCKS = {"digital": "Digital", "analog": "Analog"}
THEME_LABEL = {"dark": "Dark", "light": "Light"}

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


def _set_theme(uid: str):
    mode = st.session_state.get("pm_theme")
    if mode:
        auth.set_theme(uid, mode)
        st.session_state["theme"] = mode


def _set_clock(uid: str):
    mode = st.session_state.get("pm_clock")
    if mode:
        auth.set_clock(uid, mode)


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

        # --- appearance ---
        ui.html_block(f'<div class="lv-pm-label">{ui.esc(t("Appearance"))}</div>')
        with st.container(key="pm_look"):
            st.segmented_control(t("Theme"), list(THEME_LABEL), default=ui.valid_theme(user["theme"]), key="pm_theme",
                                 format_func=lambda m: t(THEME_LABEL[m]), label_visibility="collapsed",
                                 width="stretch", on_change=_set_theme, args=(uid,))
            ui.html_block(f'<div class="lv-pm-sub">{ui.esc(t("Clock"))}</div>')
            st.segmented_control(t("Clock"), list(CLOCKS), default=clock_mode(user), key="pm_clock",
                                 format_func=lambda m: t(CLOCKS[m]), label_visibility="collapsed",
                                 width="stretch", on_change=_set_clock, args=(uid,))

        # --- go to ---
        ui.html_block('<div class="lv-pm-sep"></div>')
        with st.container(key="pm_links"):
            st.page_link(pages["notifications"], icon=":material/notifications:",
                         label=t("Notifications") + (f"  ·  {unread}" if unread else ""))
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


def clock_mode(user) -> str:
    return user["clock"] if user["clock"] in CLOCKS else "digital"


def _now(tz_name):
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(tz_name)) if tz_name else dt.datetime.now()
    except Exception:
        return dt.datetime.now()


def _analog_svg(n) -> str:
    import math
    sec, mnt = n.second, n.minute + n.second / 60
    hr = (n.hour % 12) + mnt / 60
    ticks = "".join(
        f'<line x1="{46 + (37 if i % 3 else 34) * math.sin(i * math.pi / 6):.1f}" y1="{46 - (37 if i % 3 else 34) * math.cos(i * math.pi / 6):.1f}" '
        f'x2="{46 + 41 * math.sin(i * math.pi / 6):.1f}" y2="{46 - 41 * math.cos(i * math.pi / 6):.1f}" '
        f'stroke-width="{1.2 if i % 3 else 2.4}" stroke-linecap="round"/>' for i in range(12))
    return (f'<svg width="84" height="84" viewBox="0 0 92 92" class="lvclk-a"><circle cx="46" cy="46" r="44" fill="none" class="rim"/>'
            f'<g class="tk">{ticks}</g>'
            f'<line x1="46" y1="46" x2="46" y2="26" class="hh" stroke-width="3.4" stroke-linecap="round" transform="rotate({hr * 30:.1f} 46 46)"/>'
            f'<line x1="46" y1="46" x2="46" y2="16" class="hh" stroke-width="2.4" stroke-linecap="round" transform="rotate({mnt * 6:.1f} 46 46)"/>'
            f'<line x1="46" y1="52" x2="46" y2="12" class="sh" stroke-width="1.3" stroke-linecap="round" transform="rotate({sec * 6} 46 46)"/>'
            f'<circle cx="46" cy="46" r="2.8" class="sd"/></svg>')


@st.fragment(run_every=1)
def _tick(mode: str, tz_name: str):
    """Drawn by the server in the page itself (no iframe), so it always uses the same theme colours as the rest of the app."""
    n = _now(tz_name)
    day = ui.esc(i18n.fmt(n.date(), "%A, %b %d"))
    if mode == "analog":
        short = ui.esc(i18n.fmt(n.date(), "%a, %b %d"))
        ui.html_block(f'<div class="lvclk lvclk-row">{_analog_svg(n)}<div class="lvclk-txt"><div class="t sm">{n:%I:%M}<span class="ap"> {n:%p}</span></div>'
                      f'<div class="dt">{short}</div></div></div>')
    else:
        ui.html_block(f'<div class="lvclk"><div class="t">{n:%I:%M}<span class="s">{n:%S}</span><span class="ap"> {n:%p}</span></div>'
                      f'<div class="dt">{day}</div></div>')


def settings_link(pages: dict):
    """Settings sits under the clock at the bottom of the sidebar."""
    with st.container(key="side_settings"):
        st.page_link(pages["settings"], label=t("Settings"), icon=":material/settings:")


def clock(user):
    """A live clock pinned to the bottom of the sidebar. A fragment refreshes it every second; the rest of the page never reruns."""
    with st.container(key="side_clock"):
        _tick(clock_mode(user), getattr(st.context, "timezone", None))
