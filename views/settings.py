"""Settings, laid out like Claude's: a section list on the left, the selected section on the right."""
import datetime as dt
import json
import streamlit as st
import ai, auth, crypto, i18n, presence, privacy, session_cookie, subscription, twofa, ui
from i18n import t
from views.policy import policy

SECTIONS = ["General", "Account", "Privacy", "Billing"]
ICONS = {"General": ":material/tune:", "Account": ":material/person:", "Privacy": ":material/shield:",
         "Billing": ":material/credit_card:"}

_CSS = """<style>
.st-key-settings_nav [role="radiogroup"]{ gap: 2px; }
.st-key-settings_nav [role="radiogroup"] > label{ margin:0; padding:.5rem .75rem; border-radius:9px; width:100%;
  cursor:pointer; transition: background-color .12s ease; }
.st-key-settings_nav [role="radiogroup"] > label:hover{ background: rgba(255,255,255,.05); }
.st-key-settings_nav [role="radiogroup"] > label:has(input:checked){ background: rgba(255,255,255,.08); }
.st-key-settings_nav [role="radiogroup"] > label > div:first-child{ display:none; }
.st-key-settings_nav [role="radiogroup"] > label p{ font-size:.92rem; font-weight:500; color: var(--lv-muted); }
.st-key-settings_nav [role="radiogroup"] > label:has(input:checked) p{ color: var(--lv-text); }
.lv-set-h{ font-size:1.3rem; font-weight:620; letter-spacing:-.015em; margin: 0 0 1.2rem; color: var(--lv-text); }
.lv-set-group{ font-size:.8rem; font-weight:600; color: var(--lv-muted); letter-spacing:.07em; text-transform:uppercase;
  margin: 2rem 0 0; padding-bottom:.55rem; border-bottom:1px solid var(--lv-border); }
[class*="st-key-lvrow_"]{ padding: .85rem 0; border-bottom:1px solid var(--lv-border); gap:0; }
[class*="st-key-lvrow_"] [data-testid="stMarkdownContainer"] p{ margin-bottom:0; }
.lv-row-t{ font-size:.92rem; font-weight:500; color: var(--lv-text); }
.lv-row-d{ font-size:.82rem; color: var(--lv-muted); margin-top:.15rem; line-height:1.45; }
.lv-policy{ background: var(--lv-surface); border:1px solid var(--lv-border); border-radius:14px; padding: .4rem 1.3rem 1rem; }
.lv-policy h4{ font-size:.95rem !important; margin-top:1rem !important; }
.lv-policy p{ color:#C5CAD3; font-size:.9rem; line-height:1.6; }
</style>"""


# ---------- layout helpers ----------
def _h(text):
    ui.html_block(f'<div class="lv-set-h">{ui.esc(t(text))}</div>')


_ROWS = [0]


def _group(text):
    ui.html_block(f'<div class="lv-set-group">{ui.esc(t(text))}</div>')


def _row(title, desc=""):
    """A Claude-style settings row: label and help on the left, control on the right. Returns the right column."""
    _ROWS[0] += 1
    title, desc = t(title), t(desc) if desc else ""
    with st.container(key=f"lvrow_{_ROWS[0]}"):
        left, right = st.columns([3, 2], vertical_alignment="center")
        left.markdown(f'<div class="lv-row-t">{ui.esc(title)}</div>'
                      + (f'<div class="lv-row-d">{ui.esc(desc)}</div>' if desc else ""), unsafe_allow_html=True)
    return right


def _signed_out():
    st.session_state.clear()
    st.session_state["clear_cookie"] = True
    st.rerun()


def _ago(ts):
    s = int(dt.datetime.now().timestamp() - ts)
    return (t("Active now") if s < 120 else t("Active {n} min ago", n=s // 60) if s < 3600
            else t("Active {n} h ago", n=s // 3600))


# ---------- sections ----------
def _general(u):
    _h("General")
    _group("Profile")
    _row("Email", "Used to sign in and for security alerts.").markdown(u["email"])
    _row("Role", "Administrators can see account metadata and audit events, never case content.").markdown(
        t("Administrator") if u["role"] == "admin" else t("Member"))
    if u["created_at"]:
        _row("Member since").markdown(i18n.date_long(dt.datetime.fromtimestamp(u["created_at"])))

    _group("Language")
    cur_lang = i18n.valid(u["lang"])
    r = _row("Interface language", "Menus, messages and dates. AI answers follow it too, unless you ask in "
                                   "another language.")
    pick = r.selectbox(t("Interface language"), list(i18n.LANGS), index=list(i18n.LANGS).index(cur_lang),
                       format_func=i18n.LANGS.get, key="set_lang", label_visibility="collapsed")
    if pick != cur_lang:
        auth.set_language(u["id"], pick)
        i18n.set_lang(pick)
        st.rerun()

    _group("Presence")
    cur = presence.get_choice(u["id"])
    r = _row("Status", "Invisible shows you as offline. Do Not Disturb collects notifications without pop-ups.")
    choice = r.selectbox(t("Status"), presence.CHOICES, index=presence.CHOICES.index(cur),
                         format_func=lambda c: t(presence.CHOICE_LABEL[c]), key="set_status",
                         label_visibility="collapsed")
    if choice != cur:
        presence.set_choice(u["id"], choice)
        st.toast(t("Status updated."))

    _group("Assistant")
    r = _row("Conversation history", "Your Legal Q&A history is encrypted and visible only to you.")
    if r.button(t("Clear history"), key="set_clear_ai", use_container_width=True):
        ai.clear_history(u["id"])
        st.toast(t("Assistant history cleared."))


def _sessions(u):
    current = crypto.token_hash(st.session_state.get("token", ""))
    for s in auth.list_sessions(u["id"]):
        this = s["token_hash"] == current
        _ROWS[0] += 1
        a, b = st.container(key=f"lvrow_{_ROWS[0]}").columns([4, 1], vertical_alignment="center")
        signed_in = i18n.fmt(dt.datetime.fromtimestamp(s["created_at"]), "%b %-d, %H:%M")
        a.markdown(f'<div class="lv-row-t">{ui.esc(session_cookie.describe_device(s["user_agent"]))}'
                   f'{"&nbsp;&nbsp;<span class=lv-pill>" + ui.esc(t("This device")) + "</span>" if this else ""}</div>'
                   f'<div class="lv-row-d">{ui.esc(s["ip"] or t("Unknown IP"))} · '
                   f'{ui.esc(t("signed in {when}", when=signed_in))} · {_ago(s["last_seen"])}</div>',
                   unsafe_allow_html=True)
        if not this and b.button(t("Log out"), key=f"lo_{s['token_hash'][:12]}", use_container_width=True):
            auth.logout_session(u["id"], s["token_hash"])
            st.toast(t("That device was logged out."))
            st.rerun()


def _two_factor(u):
    if twofa.is_enabled(u["id"]):
        r = _row("Authenticator app", "On. You sign in with a code from your authenticator app.")
        with r.popover(t("Turn off"), use_container_width=True):
            with st.form("2fa_off"):
                pw = st.text_input(t("Password"), type="password")
                code = st.text_input(t("Current authenticator code"), max_chars=6)
                if st.form_submit_button(t("Turn off authenticator")):
                    ok, msg = twofa.disable(u["id"], pw, code)
                    (st.success if ok else st.error)(i18n.tm(msg))
        return
    r = _row("Authenticator app", "Stronger than email codes: works offline and stays safe if your email is "
                                  "compromised. Google Authenticator, Microsoft Authenticator, Authy or 1Password.")
    if "totp_setup" not in st.session_state:
        if r.button(t("Set up"), key="totp_go", use_container_width=True):
            st.session_state["totp_setup"] = twofa.start_setup(u["id"], u["email"])
            st.rerun()
        return
    secret, uri = st.session_state["totp_setup"]
    with st.container(border=True):
        a, b = st.columns([1, 2])
        a.image(twofa.qr_png(uri), caption=t("Scan with your app"), width=180)
        with b:
            st.markdown(t("1. Scan the QR code with your authenticator app.\n2. Can't scan? Enter this key:"))
            st.code(" ".join(secret[i:i + 4] for i in range(0, len(secret), 4)), language=None)
            with st.form("2fa_on"):
                code = st.text_input(t("3. Enter the 6-digit code it shows"), max_chars=6)
                c1, c2 = st.columns(2)
                confirm = c1.form_submit_button(t("Turn on"), type="primary", use_container_width=True)
                cancel = c2.form_submit_button(t("Cancel"), use_container_width=True)
            if confirm:
                if twofa.confirm_setup(u["id"], code):
                    st.session_state.pop("totp_setup")
                    st.success(t("Authenticator app is on."))
                    st.rerun()
                else:
                    st.error(t("That code didn't match. Check your phone's clock and try the next code."))
            if cancel:
                st.session_state.pop("totp_setup")
                st.rerun()


def _account(u):
    _h("Account")
    _group("Security")
    r = _row("Password", "Changing it signs you out everywhere.")
    with r.popover(t("Change password"), use_container_width=True):
        with st.form("chpw"):
            cur_pw = st.text_input(t("Current password"), type="password")
            new_pw = st.text_input(t("New password"), type="password",
                                   help=t("10+ characters, a letter and a number."))
            if st.form_submit_button(t("Update password"), type="primary"):
                ok, msg = auth.change_password(u["id"], cur_pw, new_pw)
                if ok:
                    _signed_out()
                else:
                    st.error(i18n.tm(msg))
    _two_factor(u)

    _group("Active sessions")
    _sessions(u)
    r = _row("Log out of all devices", "Ends every session, including this one.")
    if r.button(t("Log out everywhere"), key="lo_all", use_container_width=True):
        auth.logout_all(u["id"])
        _signed_out()

    _group("Delete account")
    r = _row("Delete account", "Permanently deletes your account, chats, documents, calendar and sessions. "
                               "This cannot be undone.")
    with r.popover(t("Delete account"), use_container_width=True):
        st.markdown(t("**This is permanent.** Export your data first from Privacy if you need it."))
        with st.form("del"):
            pw = st.text_input(t("Confirm password"), type="password")
            word = st.text_input(t("Type DELETE to confirm"))
            if st.form_submit_button(t("Delete everything"), type="primary"):
                if word == "DELETE" and crypto.verify_password(pw, u["pw_hash"]):
                    privacy.delete_account(u["id"])
                    _signed_out()
                else:
                    st.error(t("Password or confirmation incorrect."))


def _privacy(u):
    _h("Privacy")
    _group("Your data")
    r = _row("Export data", "Download everything LawVault holds about you as a JSON file.")
    data = json.dumps(privacy.export_user_data(u["id"]), indent=2, default=str)
    r.download_button(t("Export"), data, file_name="my_lawvault_data.json", mime="application/json",
                      use_container_width=True)
    _row("Personal data in AI requests", "Emails, phone, card and ID numbers are masked before any text "
                                         "leaves LawVault.").markdown("Always on")
    _row("Encryption at rest", "Case content, chat, documents, calendar titles and notifications.").markdown(
        "Always on")

    _group("Privacy policy")
    with st.container(key="policy_box"):
        st.markdown(f'<div class="lv-policy">\n\n{policy()}\n\n</div>', unsafe_allow_html=True)


def _billing(u):
    _h("Billing")
    cur = subscription.effective_plan(u)
    lim = subscription.PLANS[cur]
    used = subscription.ai_used_today(u["id"])
    c1, c2 = st.columns(2)
    c1.markdown(ui.stat("Current plan", t(lim["name"]), t("${price}/month", price=lim["price"])),
                unsafe_allow_html=True)
    c2.markdown(ui.stat("AI requests today", f"{used} / {lim['daily_ai']}", "Resets at midnight",
                        used / max(1, lim["daily_ai"])), unsafe_allow_html=True)
    if u["plan_expires"] and cur != "free":
        st.caption(t("Renews {date}", date=i18n.date_long(dt.datetime.fromtimestamp(u["plan_expires"]))))

    _group("Plans")
    cols = st.columns(len(subscription.PLANS))
    for col, (key, p) in zip(cols, subscription.PLANS.items()):
        with col.container(border=True):
            badge = f'<span class="lv-pill">{ui.esc(t("Current"))}</span>' if key == cur else "&nbsp;"
            st.markdown(f'{badge}<div class="lv-stat-value">{ui.esc(t(p["name"]))}</div>'
                        f'<div class="lv-row-d">{ui.esc(t("${price} per month", price=p["price"]))}</div>',
                        unsafe_allow_html=True)
            st.markdown("- " + t("{n} AI requests a day", n=p["daily_ai"]) + "\n- " + t("{n} cases", n=p["max_cases"])
                        + "\n- " + t("{n} documents", n=p["max_docs"]) + "\n- "
                        + t("{n} members per case", n=p["max_members"]) + "\n- "
                        + t("{n} people per meeting", n=p["max_meeting_people"]))
            if key != "free" and key != cur and st.button(t("Upgrade to {plan}", plan=t(p["name"])), key=f"up_{key}",
                                                          type="primary", use_container_width=True):
                subscription.mock_checkout(u["id"], key)
                st.rerun()
    st.caption(t("Demo checkout: no payment details are collected. A production build would use Stripe Checkout."))
    if cur != "free":
        r = _row("Cancel subscription", "You keep paid features until the end of the billing period.")
        if r.button(t("Cancel plan"), key="cancel_plan", use_container_width=True):
            subscription.cancel(u["id"])
            st.rerun()


def render():
    u = st.session_state["user"]
    _ROWS[0] = 0
    st.markdown(_CSS, unsafe_allow_html=True)
    ui.page_header("Settings")
    if st.session_state.get("settings_section") not in SECTIONS:
        st.session_state["settings_section"] = "General"
    nav, body = st.columns([1, 4], gap="large")
    with nav, st.container(key="settings_nav"):
        section = st.radio("Section", SECTIONS, key="settings_section", label_visibility="collapsed",
                           format_func=lambda s: f"{ICONS[s]}  {t(s)}")
    with body:
        {"General": _general, "Account": _account, "Privacy": _privacy, "Billing": _billing}[section](u)
