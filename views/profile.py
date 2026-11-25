"""Profile: who you are inside LawVault. Preferences and security live in Settings."""
import datetime as dt
import streamlit as st
import auth, i18n, presence, subscription, ui
from i18n import t


def display_name(u) -> str:
    return (u["display_name"] or "").strip() or u["email"].split("@")[0].replace(".", " ").title()


def render():
    u = st.session_state["user"]
    pages = st.session_state.get("_pages", {})
    ui.page_header("Profile", "How you appear to your teammates.")
    choice = presence.get_choice(u["id"])
    msg = presence.get_message(u["id"])
    plan = t(subscription.plan_info(u)["name"])
    since = i18n.date_long(dt.datetime.fromtimestamp(u["created_at"])) if u["created_at"] else ""
    ui.html_block(f"""<div class="lv-card lv-profile"><div class="lv-avatar big">{ui.esc(ui.initials(u['email']))}</div>
        <div class="lv-profile-meta"><div class="lv-profile-name">{ui.esc(display_name(u))}</div>
        <div class="lv-row-d">{ui.esc(u['email'])}{' · ' + ui.esc(u['job_title']) if u['job_title'] else ''}{' · ' + ui.esc(u['organization']) if u['organization'] else ''}</div>
        {f'<div class="lv-profile-msg">“{ui.esc(msg)}”</div>' if msg else ''}
        <div class="lv-profile-tags"><span class="lv-pill" style="color:{presence.DOT_COLOR[choice]}">● {ui.esc(t(presence.MENU_LABEL[choice]))}</span>
        <span class="lv-pill grey">{ui.esc(t("Administrator") if u['role'] == 'admin' else t("Member"))}</span>
        <span class="lv-pill grey">{ui.esc(t("{plan} plan", plan=plan))}</span></div>
        {f'<div class="lv-row-d" style="margin-top:.5rem">{ui.esc(t("Member since {date}", date=since))}</div>' if since else ''}
        </div></div>""")

    ui.section("Your details")
    with st.form("profile_form", border=False):
        name = st.text_input(t("Display name"), value=u["display_name"], max_chars=80,
                             placeholder=display_name(u) if not u["display_name"] else "")
        c1, c2 = st.columns(2)
        title = c1.text_input(t("Job title"), value=u["job_title"], max_chars=80, placeholder=t("e.g. Senior associate"))
        org = c2.text_input(t("Firm or organization"), value=u["organization"], max_chars=120)
        st.text_input(t("Email"), value=u["email"], disabled=True, help=t("Used to sign in and for security alerts."))
        if st.form_submit_button(t("Save profile"), type="primary"):
            auth.update_profile(u["id"], name, title, org)
            st.toast(t("Profile saved."))
            st.rerun()
    if "settings" in pages:
        st.caption(t("Change your availability and status message from the account menu at the top of the sidebar. Language, appearance and security are in Settings."))
        if st.button(t("Open settings"), icon=":material/settings:"):
            st.switch_page(pages["settings"])
