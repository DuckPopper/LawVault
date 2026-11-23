import base64
from pathlib import Path
import streamlit as st
import auth, i18n, otp, session_cookie, twofa
from i18n import t
from views.policy import policy

_PENDING = ("pending_uid", "pending_email", "pending_method", "dev_code", "otp_msg")


def _strength(pw: str):
    if pw:
        s = auth.password_strength(pw)
        st.progress((s + 1) / 5, text=[t("Very weak"), t("Weak"), t("Fair"), t("Good"), t("Strong")][s])


def _clear_pending():
    for k in _PENDING:
        st.session_state.pop(k, None)


_LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo.svg"
_CSS = """<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"]{ display:none; }
.st-key-auth_card{ background: var(--lv-surface); border:1px solid var(--lv-border); border-radius:18px;
  padding: 1.6rem 1.7rem 1.2rem; box-shadow: 0 30px 80px rgba(0,0,0,.35); }
.lv-auth-logo{ text-align:center; margin: 3.5rem 0 .4rem; }
.lv-auth-logo img{ height:44px; }
.lv-auth-sub{ text-align:center; color: var(--lv-muted); font-size:.92rem; margin-bottom:1.6rem; }
.lv-auth-foot{ text-align:center; color: var(--lv-muted); font-size:.75rem; margin-top:1.2rem; }
</style>"""


def _lang_picker():
    codes = list(i18n.LANGS)
    cur = i18n.lang()
    choice = st.segmented_control(t("Language"), codes, default=cur, format_func=i18n.LANGS.get, key="auth_lang",
                                  label_visibility="collapsed")
    if choice and choice != cur:
        i18n.set_lang(choice)
        st.rerun()


def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        _lang_picker()
        logo = base64.b64encode(_LOGO.read_bytes()).decode()
        st.markdown(f'<div class="lv-auth-logo"><img src="data:image/svg+xml;base64,{logo}" alt="LawVault"></div>'
                    f'<div class="lv-auth-sub">{t("The secure workspace for legal teams")}</div>', unsafe_allow_html=True)
        with st.container(key="auth_card"):
            _render_forms()
        st.markdown(f'<div class="lv-auth-foot">{t("Case data encrypted at rest · Two-step sign-in")}</div>',
                    unsafe_allow_html=True)


def _render_forms():
    if st.session_state.get("pending_uid"):
        return _second_factor()
    t_login, t_signup, t_reset = st.tabs([t("Log in"), t("Sign up"), t("Forgot password")])

    with t_login:
        with st.form("login", border=False):
            email = st.text_input(t("Email"))
            pw = st.text_input(t("Password"), type="password")
            go = st.form_submit_button(t("Continue"), type="primary", use_container_width=True)
        if go:
            status, uid, msg = auth.login_step1(email, pw)
            if status != "ok":
                st.error(i18n.tm(msg))
            elif twofa.is_enabled(uid):
                st.session_state.update(pending_uid=uid, pending_email=email, pending_method="totp",
                                        otp_msg="Open your authenticator app and enter the 6-digit code.")
                st.rerun()
            else:
                ok, m, dev = auth.start_login_otp(uid, email)
                if ok:
                    st.session_state.update(pending_uid=uid, pending_email=email, pending_method="email",
                                            dev_code=dev, otp_msg=m)
                    st.rerun()
                else:
                    st.error(i18n.tm(m))

    with t_signup:
        email = st.text_input(t("Email"), key="su_email")
        pw = st.text_input(t("Password (10+ chars, letter + number)"), type="password", key="su_pw")
        _strength(pw)
        with st.expander(t("Privacy policy")):
            st.markdown(policy())
        consent = st.checkbox(t("I have read and accept the privacy policy"))
        if st.button(t("Create account"), type="primary", use_container_width=True):
            with st.spinner(t("Checking password against known breaches…")):
                ok, msg = auth.signup(email, pw, consent, i18n.lang())
            (st.success if ok else st.error)(i18n.tm(msg))

    with t_reset:
        remail = st.text_input(t("Account email"), key="rs_email")
        if st.button(t("Send reset code")):
            msg, dev = auth.start_reset(remail)
            st.info(i18n.tm(msg))
            if dev:
                st.warning(t("DEV MODE – your code: **{code}**", code=dev))
        code = st.text_input(t("6-digit code"), key="rs_code")
        newpw = st.text_input(t("New password"), type="password", key="rs_new")
        if st.button(t("Reset password")):
            ok, msg = auth.finish_reset(remail, code, newpw)
            (st.success if ok else st.error)(i18n.tm(msg))


def _second_factor():
    method = st.session_state.get("pending_method", "email")
    uid = st.session_state["pending_uid"]
    st.subheader(t("Two-step verification"))
    st.info(i18n.tm(st.session_state.get("otp_msg", "Enter your code.")))
    if method == "email" and st.session_state.get("dev_code"):
        st.warning(t("DEV MODE – your code: **{code}** (real email is used when DEV_MODE=0)",
                     code=st.session_state["dev_code"]))
    with st.form("otp", border=False):
        label = t("Authenticator code") if method == "totp" else t("6-digit code from your email")
        code = st.text_input(label, max_chars=6)
        ok_btn = st.form_submit_button(t("Verify and log in"), type="primary", use_container_width=True)
    if ok_btn:
        if auth.is_locked(uid):
            st.error(t("Too many failed attempts. Try again in a few minutes."))
            return
        if method == "totp":
            passed = twofa.verify(uid, code)
            if not passed:
                auth.second_factor_failed(uid)
        else:
            passed = otp.verify(uid, "login", code)
        if passed:
            ua, ip = session_cookie.client_info()
            st.session_state["token"] = auth.finish_login(uid, ua, ip, session_cookie.describe_device(ua))
            st.session_state["set_cookie"] = True
            _clear_pending()
            st.rerun()
        else:
            st.error(t("Invalid or expired code."))
    c1, c2 = st.columns(2)
    if method == "email" and c1.button(t("Resend code")):
        ok, m, dev = auth.start_login_otp(uid, st.session_state["pending_email"])
        st.session_state["dev_code"] = dev
        st.session_state["otp_msg"] = m
        st.rerun()
    if method == "totp":
        c1.caption(t("Lost your phone? Ask an administrator to reset your authenticator."))
    if c2.button(t("Cancel")):
        _clear_pending()
        st.rerun()
